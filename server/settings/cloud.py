from .base import *

DEBUG = False

SECRET_KEY = get_env_value("SECRET_KEY")

# TODO:
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_WHITELIST = config("CORS_ORIGIN_WHITELIST").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env_value("POSTGRES_DATABASE"),
        "HOST": get_env_value("POSTGRES_HOST"),
        "PASSWORD": get_env_value("POSTGRES_PASSWORD"),
        "USER": get_env_value("POSTGRES_USER"),
        "PORT": 5432,
        "OPTIONS": {"ssl": {"ca": "/store_media/cert/BaltimoreCyberTrustRoot.crt.pem"}},
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = "/store_media/static"

DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"

AZURE_ACCOUNT_KEY = get_env_value("AZURE_ACCOUNT_KEY")
AZURE_URL_EXPIRATION_SECS = 300
