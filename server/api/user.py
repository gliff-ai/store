from uuid import uuid4
from datetime import datetime, timezone, timedelta
from loguru import logger
from django.shortcuts import get_object_or_404
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from ninja import Router

from django.conf import settings
from myauth.models import UserProfile, Tier, Team, Invite, User, Recovery, EmailVerification
from .billing import create_stripe_customer, create_stripe_subscription
from .schemas import (
    UserProfileIn,
    UserProfileOut,
    Error,
    InviteCreated,
    CreateInvite,
    InviteOut,
    AccountRecoveryOut,
)
import server.emails as email_template


router = Router()


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# We create a userprofile, and if a team hasn't been specified, we create them a team
@router.post("/", response={200: UserProfileOut, 409: Error, 422: Error})
def create_user(request, payload: UserProfileIn):
    user = request.auth
    if hasattr(user, "userprofile"):
        return 409, {"message": "User Exists"}

    if not payload.accepted_terms_and_conditions:
        logger.warning(f"Terms and conditions not accepted in payload ({payload.accepted_terms_and_conditions})")
        return 409, {"message": "Terms and conditions not accepted"}

    is_collaborator = False

    if payload.team_id is None:
        # Create a team for this user, and a Stripe subscription
        # use the sign up name for default team name

        if payload.tier_id:
            # Check this tier is allowed (ie it hasn't been used!). We could potentially add more checks here
            # (such as email address restrictions) but likely not needed now
            if payload.tier_id < 10000:
                return 409, {"message": "Invalid Tier ID"}

            tier = Tier.objects.get(id=payload.tier_id)

            if not tier:
                return 409, {"message": "Invalid Tier ID"}

            # Has this plan already been used?
            if Team.objects.filter(tier_id=tier.id):
                logger.error(f"Custom Tier already used - ({tier.id})")
                return 409, {"message": "This tier is unavailable"}

        else:
            tier = Tier.objects.get(name__exact=settings.DEFAULT_PLAN)

        team = Team.objects.create(owner_id=user.id, name=f"{payload.name}'s Team", tier_id=tier.id, usage=0)

        # The IP address helps us guess what tax they are going to want
        subscription, billing = create_stripe_subscription(
            user.email, payload.name, user.id, team.id, tier, get_client_ip(request)
        )

    else:
        try:
            invite = Invite.objects.get(from_team=payload.team_id, uid=payload.invite_id, email=user.email)
            invite.accepted_date = datetime.now(tz=timezone.utc)
            invite.save()

            is_collaborator = invite.is_collaborator

            team = invite.from_team

        except ObjectDoesNotExist as e:
            logger.warning(f"Received ObjectDoesNotExist error {e}")
            return 409, {"message": "Invalid invitation"}

    user_profile = UserProfile.objects.create(
        user_id=user.id,
        team_id=team.id,
        name=payload.name,
        recovery_key=payload.recovery_key,
        accepted_terms_and_conditions=datetime.now(tz=timezone.utc),
        is_collaborator=is_collaborator,
    )
    user_profile.id = user_profile.user_id  # The frontend expects id not user_id
    user_profile.email = user.email
    user_profile.save()

    user.is_active = False
    user.userprofile = user_profile

    user.save()

    # Send verification email
    uid = str(uuid4())
    now = datetime.now(tz=timezone.utc)
    now_plus_24h = now + timedelta(hours=24)

    validation = EmailVerification.objects.create(uid=uid, user_profile=user.userprofile, expiry_date=now_plus_24h)
    validation.save()

    logger.info("email verification request created")
    try:
        message = Mail(
            from_email="contact@gliff.ai",
            to_emails=user.email,
        )
        message.dynamic_template_data = {
            "verify_url": settings.BASE_URL + "/verify_email/" + uid,
        }
        message.template_id = email_template.id["verify_email"]

        sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sendgrid_client.send(message)
    except Exception as e:
        logger.error(e)

    return user_profile


@router.get("/", response={200: UserProfileOut, 204: None})
def get_user(request):
    try:
        user = request.auth
        user.userprofile.id = user.id
        user.userprofile.email = user.email

        return user.userprofile
    except UserProfile.DoesNotExist:
        return 204, None


@router.put("/", response=UserProfileOut)  # Update a user profile
def update_user(request, payload: UserProfileIn):
    user = request.auth

    # You can only actually change a recovery key
    user.userprofile.recovery_key = payload.recovery_key

    user.userprofile.save()

    user.userprofile.id = user.id
    user.userprofile.email = user.email

    return user.userprofile


@router.post("/invite/", response={200: InviteCreated, 409: Error, 500: Error})
def create_invite_user(request, payload: CreateInvite):
    return create_invite(request, payload.email, False)


@router.post("/invite/collaborator/", response={200: InviteCreated, 409: Error, 500: Error})
def create_invite_collaborator(request, payload: CreateInvite):
    return create_invite(request, payload.email, True)


def create_invite(request, email, is_collaborator):
    try:
        uid = str(uuid4())
        user = request.auth

        team = Team.objects.get(owner_id=user.id)

        try:
            invitee = User.objects.get(email=email)
            if invitee is not None:
                return 409, {"message": "user is already on a team"}

        except ObjectDoesNotExist as e:
            logger.info(f"Received ObjectDoesNotExist error {e}")
            pass

        invite = Invite.objects.create(uid=uid, email=email, from_team_id=team.id, is_collaborator=is_collaborator)

        invite.save()

        logger.info("invite created")
        try:
            # TODO email sending should be a function

            # TODO slightly different email for a collaborator?
            message = Mail(
                from_email="contact@gliff.ai",
                to_emails=email,
            )
            message.dynamic_template_data = {
                "invite_url": settings.BASE_URL + "/signup?invite_id=" + uid,
            }
            message.template_id = email_template.id["invite_to_team"]

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sendgrid_client.send(message)
        except Exception as e:
            logger.error(f"sending invite email {e}")

        return 200, {"id": uid}

    except IntegrityError as e:
        logger.warning(f"Received IntegrityError {e}")
        return 409, {"message": "user is already invited to a team"}

    except Exception as e:
        logger.warning(f"Received Exception {e}")
        return 500, {"message": "unknown error"}


### These routes have no auth as user either won't have an account or won't be logged in when they are used
@router.post("/verify_email", auth=None, response={201: None, 409: Error})
def request_validation_email(request, payload: CreateInvite):
    try:
        user = User.objects.get(email=payload.email)
        if user is None:
            logger.info("trying to recover an account that doesn't exist")
            return 201, None  # Not a user, but don't tell anyone that!

    except ObjectDoesNotExist:
        logger.info("trying to recover an account that doesn't exist")
        return 201, None  # Not a user, but don't tell anyone that!

    try:
        uid = str(uuid4())
        now = datetime.now(tz=timezone.utc)
        now_plus_24h = now + timedelta(hours=24)

        validation = EmailVerification.objects.create(uid=uid, user_profile=user.userprofile, expiry_date=now_plus_24h)
        validation.save()

        logger.info("email verification request created")
        try:
            message = Mail(
                from_email="contact@gliff.ai",
                to_emails=user.email,
            )
            message.dynamic_template_data = {
                "verify_url": settings.BASE_URL + "/verify_email/" + uid,
            }
            message.template_id = email_template.id["verify_email"]

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sendgrid_client.send(message)
        except Exception as e:
            logger.error(e)

        return 201, None

    except Exception as e:
        logger.warning(f"Received Exception {e}, Invalid Email Verification")
        return 409, None


@router.get("/invite", auth=None, response={200: InviteOut, 404: None})
def accept_invite(request, invite_id: str):
    try:
        invite = Invite.objects.get(uid=invite_id)
    except ObjectDoesNotExist as e:
        logger.info(f"Received ObjectDoesNotExist error {e}")
        return 404, None

    if invite.accepted_date is not None:
        return 500

    return 200, {"email": invite.email, "team_id": invite.from_team.id}


@router.post("/recover", auth=None, response=None)
def create_recovery(request, payload: CreateInvite):
    try:
        user = User.objects.get(email=payload.email)
        if user is None:
            logger.info("trying to recover an account that doesn't exist")
            return 201  # Not a user, but don't tell anyone that!

    except ObjectDoesNotExist:
        logger.info("trying to recover an account that doesn't exist")
        return 201  # Not a user, but don't tell anyone that!

    try:
        uid = str(uuid4())
        now = datetime.now(tz=timezone.utc)
        now_plus_10 = now + timedelta(minutes=10)
        recovery = Recovery.objects.create(uid=uid, user_profile=user.userprofile, expiry_date=now_plus_10)

        recovery.save()

        logger.info("recovery key created")
        try:
            message = Mail(
                from_email="contact@gliff.ai",
                to_emails=payload.email,
            )
            message.dynamic_template_data = {
                "recovery_url": settings.BASE_URL + "/recover?uid=" + uid,
            }
            message.template_id = email_template.id["recover_account"]

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sendgrid_client.send(message)
        except Exception as e:
            logger.error(e)

        return 201

    except Exception as e:
        logger.warning(f"Received Exception {e}")
        return 201


@router.get("/recover/{recovery_id}", auth=None, response={200: AccountRecoveryOut, 404: None})
def get_recovery(request, recovery_id: str):
    try:
        recovery = get_object_or_404(Recovery, uid=recovery_id)

        recovery_key = UserProfile.objects.filter(
            user_id=recovery.user_profile_id, recovery__expiry_date__gte=datetime.now(tz=timezone.utc)
        ).values("recovery_key")[0]

        return recovery_key

    except Exception as e:
        logger.warning(f"Received Exception {e}, Invitation Expired")
        return 404, None


@router.get("/verify_email/{verification_id}", auth=None, response={200: None, 403: None})
def verify_email(request, verification_id: str):
    try:
        validation = get_object_or_404(
            EmailVerification, uid=verification_id, expiry_date__gte=datetime.now(tz=timezone.utc)
        )

        profile = UserProfile.objects.get(user_id=validation.user_profile_id)

        profile.email_verified = datetime.now(tz=timezone.utc)

        profile.save()

        user = get_object_or_404(User, id=validation.user_profile_id)
        user.is_active = True

        user.save()

        # Send welcome email
        try:
            message = Mail(
                from_email="contact@gliff.ai",
                to_emails=profile.user.email,
            )

            message.template_id = email_template.id["welcome"]

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sendgrid_client.send(message)
        except Exception as e:
            logger.error(e)

        return 200, None

    except Exception as e:
        logger.warning(f"Received Exception {e}, Invalid Email Verification")
        return 403, None
