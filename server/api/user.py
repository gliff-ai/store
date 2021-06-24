from uuid import uuid4
from datetime import datetime, timezone, timedelta

from django.shortcuts import get_object_or_404
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from ninja import Router

from django.conf import settings
from myauth.models import UserProfile, Tier, Team, Invite, User, Recovery
from .schemas import (
    UserProfileIn,
    UserProfileOut,
    Error,
    InviteCreated,
    CreateInvite,
    InviteOut,
    AccountRecoveryOut,
)

from loguru import logger

router = Router()


# We create a userprofile, and if a team hasn't been specified, we create them a team
@router.post("/", response={200: UserProfileOut, 409: Error})
def create_user(request, payload: UserProfileIn):
    user = request.auth

    if hasattr(user, "userprofile"):
        return 409, {"message": "User Exists"}

    if payload.team_id is None:
        # Create a team for this user. All teams are on the basic plan until we have processed payment
        tier = Tier.objects.get(name__exact="COMMUNITY")
        team = Team.objects.create(owner_id=user.id, tier_id=tier.id)
    else:
        try:
            invite = Invite.objects.get(from_team=payload.team_id, uid=payload.invite_id, email=user.email)
            invite.accepted_date = datetime.now(tz=timezone.utc)
            invite.save()

            team = invite.from_team

        except ObjectDoesNotExist as e:
            logger.warning(f"Received ObjectDoesNotExist error {e}")
            return 409, {"message": "Invalid invitation"}

    user_profile = UserProfile.objects.create(
        user_id=user.id,
        team_id=team.id,
        name=payload.name,
        recovery_key=payload.recovery_key,
    )

    user.save()
    user_profile.id = user_profile.user_id  # The frontend expects id not user_id
    user_profile.email = user.email
    return user_profile


@router.get("/", response=UserProfileOut)
def get_user(request):
    user = request.auth
    user.userprofile.id = user.id

    return user.userprofile


@router.put("/", response=UserProfileOut)  # Update a user profile
def update_user(request, payload: UserProfileIn):
    user = request.auth

    # You can only actually change a recovery key
    user.userprofile.recovery_key = payload.recovery_key

    user.userprofile.save()

    user.userprofile.id = user.id
    return user.userprofile


@router.post("/invite", response={200: InviteCreated, 409: Error, 500: Error})
def create_invite(request, payload: CreateInvite):
    try:
        uid = str(uuid4())
        user = request.auth

        team = Team.objects.get(owner_id=user.id)

        try:
            invitee = User.objects.get(email=payload.email)
            if invitee is not None:
                return 409, {"message": "user is already on a team"}

        except ObjectDoesNotExist as e:
            logger.info(f"Received ObjectDoesNotExist error {e}")
            pass

        invite = Invite.objects.create(uid=uid, email=payload.email, from_team_id=team.id)

        invite.save()

        print("invite created")
        try:
            message = Mail(
                from_email="support@gliff.app",
                to_emails=payload.email,
            )
            message.dynamic_template_data = {
                "invite_url": settings.BASE_URL + "/signup?invite_id=" + uid,
            }
            message.template_id = "d-4e62eee5c6b84a56b4225a2c3faa4c32"

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sendgrid_client.send(message)
            print(response.status_code)
            print(response.body)
            print(response.headers)
        except Exception as e:
            print(e)

        return 200, {"id": uid}

    except IntegrityError as e:
        logger.warning(f"Received IntegrityError {e}")
        return 409, {"message": "user is already invited to a team"}

    except Exception as e:
        logger.warning(f"Received Exception {e}")
        return 500, {"message": "unknown error"}


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
            print("Recovering none existent account")
            return 201  # Not a user, but don't tell anyone that!

    except ObjectDoesNotExist as e:
        print("Recovering none existent account")
        return 201  # Not a user, but don't tell anyone that!

    try:
        uid = str(uuid4())
        now = datetime.now(tz=timezone.utc)
        now_plus_10 = now + timedelta(minutes=10)
        recovery = Recovery.objects.create(uid=uid, user_profile=user.userprofile, expiry_date=now_plus_10)

        recovery.save()

        print("recovery created")
        try:
            message = Mail(
                from_email="support@gliff.app",
                to_emails=payload.email,
            )
            message.dynamic_template_data = {
                "recovery_url": settings.BASE_URL + "/recover?uid=" + uid,
            }
            message.template_id = "d-88b2e30576724d459416ea5dbd932ac7"

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sendgrid_client.send(message)
        except Exception as e:
            print(e)

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
