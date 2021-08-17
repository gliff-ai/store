from datetime import datetime

from loguru import logger
import stripe
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management.base import BaseCommand
from myauth.models import Team, User, Billing, Tier
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import server.emails as email_template
from server.api.billing import gliff_to_stripe_usage, stripe_to_gliff_usage

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_container_client():
    from azure.storage.blob import ContainerClient

    connection_string = f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_ACCOUNT_NAME};AccountKey={settings.AZURE_ACCOUNT_KEY}"
    return ContainerClient.from_connection_string(conn_str=connection_string, container_name=settings.AZURE_CONTAINER)


def update_stripe_usage(subscription_id, storage_price_ids, usage, team_id):
    # Get the storage price id
    subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price.tiers"])

    user_price_id, stripe_price_id, tiers = next(
        (
            (item.id, item.price["id"], item.price["tiers"])
            for item in subscription["items"]["data"]
            if item.price["id"] in storage_price_ids
        ),
        None,
    )

    if user_price_id:
        stripe.SubscriptionItem.create_usage_record(
            user_price_id,
            action="set",
            quantity=gliff_to_stripe_usage(usage),
            timestamp=datetime.now(),
        )
    else:
        logger.warning(f"Team {team_id} doesn't have a valid storage price set")

    limit = stripe_to_gliff_usage(tiers[0].up_to)

    # We probably don't want to alert this _every_ night
    if usage / limit > 0.9:
        logger.warning(
            f"Subscription exceeds 90% of free usage for team {team_id},  (Using {gliff_to_stripe_usage(usage)}Gb)"
        )
    else:
        logger.debug(f"Subscription storage is at {(usage / limit) * 100}% for team {team_id}")
    return


def suspend_trial_account(team_id):
    try:
        users = User.objects.filter(team=team_id)
        team = Team.objects.get(id=team_id)
        owner_email = team.owner.email

        # Are they already suspended?
        if team.owner.is_active is not True:
            return

        logger.warning(f"Suspending free account {team_id}")
        # We want to use our own (non-etebase) flag for this at some point and use some middleware to handle this
        # For now tho, this is crude and effective
        users.update(is_active=False)

        try:
            message = Mail(
                from_email="contact@gliff.ai",
                to_emails=owner_email,
            )

            message.template_id = email_template.id["free_exceeded_limit"]

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sendgrid_client.send(message)
        except Exception as e:
            logger.error(e)
    except Exception as e:
        logger.error(e)


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
            usage = round(data_select[user_id] * 10 ** -6)
            teams[user.team.id] = teams.get(user.team.id, 0) + usage
            logger.info(f"Updated team {user.team.id} with {user_id}: new usage = {teams[user.team.id]}")

    # Stripe Price IDs
    price_ids = Tier.objects.all().values_list("stripe_storage_price_id", flat=True)

    for key in teams:
        team = Team.objects.get(id=key)
        team.usage = teams[key]
        team.save()

        try:
            subscription_id = team.billing.subscription_id
            update_stripe_usage(subscription_id, price_ids, team.usage, team.id)
        except Billing.DoesNotExist:
            if team.usage < 9000:
                logger.info(f"Team {team.id} doesn't have billing. Their usage is {team.usage}")
            else:
                logger.warning(f"Team {team.id} doesn't have billing. Their usage is {team.usage}")
                suspend_trial_account(team.id)


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
