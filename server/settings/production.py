from .cloud import *

BASE_URL = "https://gliff.app"
SUCCESS_URL = BASE_URL + "/signup/success"
CANCEL_URL = BASE_URL + "/signup/cancel"

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
    release=VERSION,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=0.1,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
    environment="production",
    debug=False,
)
