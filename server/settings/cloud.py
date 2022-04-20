from .base import *
import sentry_sdk
from sentry_sdk.scope import add_global_event_processor
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import (
    LoggingIntegration,
    BreadcrumbHandler,
    EventHandler,
)
from loguru import logger

DEBUG = False

SECRET_KEY = get_env_value("SECRET_KEY")

# TODO:
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_WHITELIST = config("CORS_ORIGIN_WHITELIST").split(",")

HOST = "0.0.0.0"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env_value("POSTGRES_DATABASE"),
        "HOST": get_env_value("POSTGRES_HOST"),
        "PASSWORD": get_env_value("POSTGRES_PASSWORD"),
        "USER": get_env_value("POSTGRES_USER"),
        "PORT": 5432,
        "CONN_MAX_AGE": None,
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = "/store_media/static"

## Logging settings
# sentry breadcrumbs are sent only when an 'event' is captured and provide extra info
logger.add(
    BreadcrumbHandler(level="DEBUG"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    diagnose=True,  # set to False for production
    level="DEBUG",
)

# sentry events are the errors and exceptions that we want to catch
logger.add(
    EventHandler(level="ERROR"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    diagnose=True,  # set to False for production
    level="ERROR",
)

LOG_LEVEL = "DEBUG"  # used for intercepting uvicorn and django logs, which use Python's own logging


@add_global_event_processor
def ignore_healthcheck(event, hint):
    # filter for sentry to ignore /api/ healthcheck hits
    # see: https://docs.sentry.io/platforms/python/configuration/filtering/
    if event.get("transaction") == "/api/" or event.get("transaction") == "/api":
        return None
    return event


# vars used in background tasks
RUN_TASK_UPDATE_STORAGE = get_env_value("RUN_TASK_UPDATE_STORAGE")
TASK_UPDATE_STORAGE_HOUR = get_env_value("TASK_UPDATE_STORAGE_HOUR")
TASK_UPDATE_STORAGE_MINUTE = get_env_value("TASK_UPDATE_STORAGE_MINUTE")
