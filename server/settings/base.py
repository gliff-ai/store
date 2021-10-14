"""
Base Django settings.

These can be used locally, and are extended for deployment (and then selected by setting DJANGO_SETTINGS_MODULE)
"""

import os
from decouple import config
from django.core.exceptions import ImproperlyConfigured

VERSION = "store@1.7.0"


# Use this if you want to enforce an env var being set. If you want a default, just use decouple directly
def get_env_value(env_variable):
    try:
        return config(env_variable)
    except KeyError:
        error_msg = "Set the {} environment variable".format(env_variable)
        raise ImproperlyConfigured(error_msg)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_USER_MODEL = "myauth.User"

SECRET_KEY = "VERYVERYVERYVERYVERYVERYSECRETKEY"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
LOG_LEVEL = "DEBUG"  # used for intercepting uvicorn and django logs, which use Python's own logging

ALLOWED_HOSTS = ["*"]

HOST = "127.0.0.1"

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_WHITELIST = config("CORS_ORIGIN_WHITELIST").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("ETEBASE_DB_PATH", os.path.join(BASE_DIR, "../", "db.sqlite3")),
    }
}

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "myauth.apps.GliffAuthConfig",
    "django_etebase.apps.DjangoEtebaseConfig",
    "django_etebase.token_auth.apps.TokenAuthConfig",
    "django_apscheduler",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_URL = "/static/"
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT")

MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT", os.path.join(BASE_DIR, "../", "media"))
MEDIA_URL = "/user-media/"

STRIPE_SECRET_KEY = get_env_value("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = get_env_value("STRIPE_WEBHOOK_SECRET")

SENDGRID_API_KEY = get_env_value("SENDGRID_API_KEY")

BASE_URL = config("BASE_URL", default="http://localhost:3000")

SUCCESS_URL = config("SUCCESS_URL", default="http://localhost:3000/signup/success")
CANCEL_URL = config("CANCEL_URL", default="http://localhost:3000/signup/cancel")

# vars used in background tasks
RUN_TASK_UPDATE_STORAGE = False
