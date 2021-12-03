import os

# These NEED setting but it fails relatively gracefully, so set them to anything.
# We actually overwrite them later to make sure they're not set
os.environ["STRIPE_SECRET_KEY"] = "-"
os.environ["STRIPE_WEBHOOK_SECRET"] = "-"
os.environ["SENDGRID_API_KEY"] = "-"

from .base import *  # noqa: E402

STRIPE_SECRET_KEY = "-"
STRIPE_WEBHOOK_SECRET = "-"
SENDGRID_API_KEY = "-"

DEBUG = False
TEST_MODE = True
