from loguru import logger
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management.base import BaseCommand


def get_container_client():
    from azure.storage.blob import ContainerClient

    connection_string = f"DefaultEndpointsProtocol=https;AccountName={settings.AZURE_ACCOUNT_NAME};AccountKey={settings.AZURE_ACCOUNT_KEY}"
    return ContainerClient.from_connection_string(conn_str=connection_string, container_name=settings.AZURE_CONTAINER)


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
    from myauth.models import Team

    for team in Team.objects.all():

        user_id = str(team.id)
        if user_id in user_ids:
            # store usage in Mb and save team
            team.usage = data_select[user_id] * 10 ** -6
            team.save()
            logger.info(f"Updated team {team.id}: new usage = {team.usage}")


class Command(BaseCommand):
    def handle(self, *args, **options):

        # add scheduler that runs in the brackground within the application.
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
