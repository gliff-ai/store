from typing import List

from ninja import NinjaAPI, Schema
from ninja.security import APIKeyHeader
from ninja.orm import create_schema

from etebase_fastapi.dependencies import get_authenticated_user
from django.shortcuts import get_object_or_404
from myauth.models import User, UserProfile, Tier, Team


class ApiKey(APIKeyHeader):
    param_name = "Authorization"

    def authenticate(self, request, key):
        user = get_authenticated_user(key) # Validate with Etebase
        return user

api = NinjaAPI(auth=ApiKey())

TierSchema = create_schema(Tier)

class UserProfileIn(Schema):
    first_name: str
    last_name: str
    team_id: int = None
    recovery_key: str = None

class TeamSchema(Schema):
    id: int
    owner_id: int
    tier: TierSchema


class UserProfileOut(Schema):
    id: int
    first_name: str
    last_name: str
    team: TeamSchema


@api.get("/", auth=None)
def hello(request):
    return "Hello World"


@api.get("/tier", response=List[TierSchema], auth=None)
def list_tiers(request):
    return Tier.objects.all()


# Users (login and logout are handled by etebase_server and the etebase SDK F.E.

# We create a userprofile, and if a team hasn't been specified, we create them a team
@api.post("/user", response=UserProfileOut)
def create_user(request, payload: UserProfileIn):
    user = request.auth

    if hasattr(user, "userprofile"):
        return api.create_response(
            request,
            {"message": "User Exists"},
            status=409,
        )

    if payload.team_id is None:
        # Create a team for this user. All teams are on the basic plan until we have processed payment
        tier = Tier.objects.get(name__exact="COMMUNITY")
        team = Team.objects.create(owner_id=user.id, tier_id=tier.id)
    else:
        # TODO  We need a way to check they have been invited to a team, otherwise you could join any team
        team = Team.objects.get(id=payload.team_id)

    # TODO encrypt recovery key

    UserProfile.objects.create(user_id=user.id, team_id=team.id, first_name=payload.first_name, last_name=payload.last_name)

    user.save()
    return user.userprofile


@api.get("/user", response=UserProfileOut)
def get_user(request):
    user = request.auth
    user.userprofile.id = user.id

    return user.userprofile

#
@api.put("/user", response=UserProfileOut)  # Update a user profile
def update_user(request, payload: UserProfileIn):
    user = request.auth

    # You can only actually change name for now...
    user.userprofile.first_name = payload.first_name
    user.userprofile.last_name = payload.last_name

    user.userprofile.save()

    user.userprofile.id = user.id
    return user.userprofile
