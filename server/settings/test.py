import os
from decouple import config

# These NEED setting but it fails relatively gracefully, so set them to anything.
# We actually overwrite them later to make sure they're not set
os.environ["SENDGRID_API_KEY"] = "-"
os.environ["STRIPE_WEBHOOK_SECRET"] = "-"

try:
    STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
except Exception as e:
    print("STRIPE_SECRET_KEY is not set. This is OK, but if you run the Billing tests, you should set it")
    os.environ["STRIPE_SECRET_KEY"] = "-"

from .base import *  # noqa: E402

STRIPE_WEBHOOK_SECRET = "-"
SENDGRID_API_KEY = "-"

DEBUG = False
TEST_MODE = True
