from uuid import uuid4
from datetime import datetime, timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from ninja import Router

from django.conf import settings
from myauth.models import UserProfile, Tier, Team, Invite, User
from .schemas import (
    UserProfileIn,
    UserProfileOut,
    Error,
    InviteCreated,
    CreateInvite,
    InviteOut,
)


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
            invite = Invite.objects.get(
                from_team=payload.team_id, uid=payload.invite_id, email=user.email
            )
            invite.accepted_date = datetime.now(tz=timezone.utc)
            invite.save()

            team = invite.from_team

        except ObjectDoesNotExist as e:
            return 409, {"message": "Invalid invitation"}

    user_profile = UserProfile.objects.create(
        user_id=user.id,
        team_id=team.id,
        name=payload.name,
        recovery_key=payload.recovery_key.encode(),
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

    # You can only actually change name for now...
    user.userprofile.first_name = payload.first_name
    user.userprofile.last_name = payload.last_name

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
            pass

        invite = Invite.objects.create(
            uid=uid, email=payload.email, from_team_id=team.id
        )

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
        print(e)
        return 409, {"message": "user is already invited to a team"}

    except Exception as e:
        return 500, {"message": "unknown error"}


@router.get("/invite", auth=None, response={200: InviteOut, 404: None})
def accept_invite(request, invite_id: str):
    try:
        invite = Invite.objects.get(uid=invite_id)
    except ObjectDoesNotExist as e:
        return 404, None

    if invite.accepted_date is not None:
        return 500

    return 200, {"email": invite.email, "team_id": invite.from_team.id}
