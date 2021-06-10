from uuid import uuid4
from datetime import datetime, timezone

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django_etebase.models import Collection, CollectionInvitation
from etebase_fastapi.routers.invitation import CollectionInvitationIn
from etebase_fastapi.utils import get_object_or_404, Context
from ninja import Router

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


def create_outgoing_etebase_invite(from_team, to_user):
    to_user = User.objects.get(id=to_user)

    from_user = User.objects.get(team__id=from_team)

    # TODO invite to ALL collections
    collection = Collection.objects.all().filter(owner_id=from_user.id)

    # This is what etebase would expect in the request
    data: CollectionInvitationIn = CollectionInvitationIn(
        uid=str(uuid4()),
        version=1,
        accessLevel=2,  # R/W
        username=to_user.username,
        collection=collection[0].id,
        signedEncryptionKey=(1024).to_bytes(2, byteorder="big"),  # We don't use this!
    )

    context = Context(from_user, None)
    data.validate_db(context)

    # We shouldn't need this?
    # if not is_collection_admin(collection, user):
    #     raise PermissionDenied(
    #         "admin_access_required", "User is not an admin of this collection"
    #     )

    member = collection[0].members.get(user=from_user)

    with transaction.atomic():
        try:
            CollectionInvitation.objects.create(
                **data.dict(exclude={"collection", "username"}),
                user=to_user,
                fromMember=member
            )
        except IntegrityError:
            print("invitation_exists")


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

            create_outgoing_etebase_invite(payload.team_id, user.id)

            # TODO accept etebase invites if possible?

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
        uid = uuid4()
        user = request.auth
        team = Team.objects.get(owner_id=user.id)

        invite = Invite.objects.create(
            uid=id, email=payload.email, from_team_id=team.id
        )

        invite.save()

        # TODO email the invite!

        return 200, {"id": uid}

    except IntegrityError as e:
        return 409, {"message": "user is already invited to a team"}

    except Exception as e:
        return 500, {"message": "unknown error"}  # 500?


@router.get("/invite", auth=None, response={200: InviteOut, 404: None})
def accept_invite(request, invite_id: str):
    try:
        invite = Invite.objects.get(uid=invite_id)
    except ObjectDoesNotExist as e:
        return 404, None

    if invite.accepted_date is not None:
        return 500

    return 200, {"email": invite.email, "team_id": invite.from_team.id}
