from datetime import datetime

from loguru import logger
import stripe
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management.base import BaseCommand
from myauth.models import Team, User, Billing, Tier

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_container_client():
    from azure.storage.blob import ContainerClient

    connection_string = f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_ACCOUNT_NAME};AccountKey={settings.AZURE_ACCOUNT_KEY}"
    return ContainerClient.from_connection_string(conn_str=connection_string, container_name=settings.AZURE_CONTAINER)


def update_stripe_usage(subscription_id, storage_price_ids, usage):
    # Get the storage price id
    subscription = stripe.Subscription.retrieve(subscription_id)

    price_id = next(
        (item.id for item in subscription["items"]["data"] if item.price["id"] in storage_price_ids),
        None,
    )

    if price_id:
        stripe.SubscriptionItem.create_usage_record(
            price_id,
            quantity=usage,
            timestamp=datetime.now(),
        )
    else:
        logger.warning(f"User doesn't have a valid storage price set - {subscription_id}")

    return


def update_team_storage_usage():
    try:
        # get container client
        container = get_container_client()

        # get list of all blobs
        blob_list = container.list_blobs()
    except Exception as e:
        logger.error(f"Received Exception {e}, Update team usage")
        pass

    # save data in a dictionary of type { name: size }
    # necessary step because can iterate through blob_list only once
    data = {blob.name: blob.size for blob in blob_list}

    logger.info("Got blob data")

    data_select = dict()
    for key, value in data.items():
        try:
            user_id = key.split("_")[1].split("/")[0]
            try:
                data_select[user_id] += value
            except KeyError:
                data_select[user_id] = value
        except AttributeError:
            logger.error(f"Key {key}: Unexpected format.")

    user_ids = data_select.keys()

    teams = dict()
    for user in User.objects.all():
        user_id = str(user.id)
        if user_id in user_ids:
            # Add this users usage to their team usage
            usage = data_select[user_id] * 10 ** -6
            teams[user.team.id] = teams.get(user.team.id, 0) + usage
            logger.info(f"Updated team {user.team.id} with {user_id}: new usage = {teams[user.team.id]}")

    # Stripe Price IDs
    price_ids = Tier.objects.all().values_list("stripe_storage_price_id", flat=True)

    for key in teams:
        team = Team.objects.get(id=key)
        team.usage = teams[key]
        team.save()
        update_stripe_usage(team.billing.subscription_id, price_ids, team.usage)
        # TODO check their limits?


class Command(BaseCommand):
    def handle(self, *args, **options):

        # add scheduler that runs in the background within the application.
        job_defaults = {"coalesce": True, "max_instances": 1}
        scheduler = BackgroundScheduler(job_defaults=job_defaults, timezone="UTC")

        # the default database for job store is PostgresSQL (called SQLAlchemyJobStore)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # schedule jobs to run every day at hour:minute UTC
        scheduler.add_job(
            update_team_storage_usage,
            "cron",
            hour=settings.TASK_UPDATE_STORAGE_HOUR,
            minute=settings.TASK_UPDATE_STORAGE_MINUTE,
            id="update_team_storage_usage",
            replace_existing=True,
        )
        logger.info("Added daily job: 'update_team_storage_usage'.")

        try:
            logger.info("Scheduler starting..")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopping..")
            scheduler.shutdown()
