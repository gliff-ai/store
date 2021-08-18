from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from ninja import Router
from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from myauth.models import UserProfile, Tier, Team, User, Invite
from .schemas import UserProfileOut, InvitedProfileOut, TeamsOut, Error, CreateInvite
import server.emails as email_template

router = Router()


@router.post(
    "/collaborate",
    response={200: None, 500: Error},
)
def email_collab(request, payload: CreateInvite):
    user = request.auth
    message = Mail(
        from_email="contact@gliff.ai",
        to_emails=payload.email,
    )

    try:
        # User exists, so just tell them they have an invite
        User.objects.get(email=payload.email)
        message.template_id = email_template.id["collaborate_existing_user"]

    except ObjectDoesNotExist as e:
        # User doesn't exist so send them a slightly different email
        message.template_id = email_template.id["collaborate_new_user"]

        logger.info(f"Received ObjectDoesNotExist error {e}")

    try:
        message.dynamic_template_data = {"site_url": settings.BASE_URL, "user_name": user.userprofile.name}

        sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sendgrid_client.send(message)
    except Exception as e:
        logger.error(f"sending collab email {e}")
        return 500, {"message": "unknown error"}

    return 200, None
