import os
import logging
import django
from uvicorn import Config, Server
from loguru import logger
from django.conf import settings
from django.core import management

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")


class InterceptHandler(logging.Handler):
    """
    Intercept all default Python logging statements and send to loguru.
    """

    def emit(self, record):
        # get corresponding loguru level if it exists
        # if not, use the level number
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # find caller from where originated the logged message
        # TODO is the while loop needed at all?
        frame, depth = logging.currentframe(), 2
        while depth < 2 + 5:  # frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # send loguru statement, making sure we raise an exception where we should
        logger.opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


def setup_logging():
    # intercept everything at the root logger at level as per the settings files
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LOG_LEVEL)

    # remove every other logger's handlers
    # and propagate them to the root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


django.setup()

# Has to come after django setup
from server.asgi import get_application  # noqa: E402

# start the asynchronous web app server
app = get_application()

# setup logging last, to make sure no library overwrites it
# (they shouldn't, but it happens)
setup_logging()

if settings.RUN_TASK_UPDATE_STORAGE:
    # run background task for updating all team's storage usage
    management.call_command("update_team_storage_usage")

if __name__ == "__main__":
    # initialise uvicorn server
    server = Server(
        Config(
            app=app,
            host=settings.HOST,
            log_level=settings.LOG_LEVEL.lower(),  # annoyingly uses lowercase log levels
        ),
    )

    # run the thing
    server.run()
