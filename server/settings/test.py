import os

# These NEED setting but it fails relatively gracefully, so set them to anything
os.environ["STRIPE_SECRET_KEY"] = "-"
os.environ["STRIPE_WEBHOOK_SECRET"] = "-"
os.environ["SENDGRID_API_KEY"] = "-"

from .base import *

DEBUG = False
