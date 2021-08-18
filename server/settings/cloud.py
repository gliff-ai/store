from .base import *
import sentry_sdk
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
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = "/store_media/static"

DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"

AZURE_ACCOUNT_KEY = get_env_value("AZURE_ACCOUNT_KEY")
AZURE_ACCOUNT_NAME = get_env_value("AZURE_ACCOUNT_NAME")
AZURE_CONTAINER = get_env_value("AZURE_CONTAINER")
AZURE_URL_EXPIRATION_SECS = 300

## Logging settings
# Set-up sentry connection
sentry_sdk.init(
    # should this be a secret?
    dsn="https://95bd2160e76b4046b112eb551e89f4e4@o651808.ingest.sentry.io/5828719",
    # integrate with Django (just in case) but disable Python Logging integration (as we use loguru)
    integrations=[
        DjangoIntegration(),
        LoggingIntegration(level=None, event_level=None),
    ],
    release="store@1.5.0",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
    # flag for filtering
    environment="staging",  # set to "production" for production
    debug=True,  # set to False for production
)

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

# vars used in background tasks
RUN_TASK_UPDATE_STORAGE = get_env_value("RUN_TASK_UPDATE_STORAGE")
TASK_UPDATE_STORAGE_HOUR = get_env_value("TASK_UPDATE_STORAGE_HOUR")
TASK_UPDATE_STORAGE_MINUTE = get_env_value("TASK_UPDATE_STORAGE_MINUTE")
