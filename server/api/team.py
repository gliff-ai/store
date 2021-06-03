from typing import List

from ninja import Router

from myauth.models import UserProfile, Tier, Team, User
from .schemas import UserProfileOut

router = Router()


@router.get("/", response=List[UserProfileOut])
def get_team(request):
    user = request.auth

    # is the user the owner of the team?
    user.userprofile.id = user.id

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can view the team"}

    users = User.objects.filter(team__owner=user.id)

    profiles = []
    for user in users:
        user.userprofile.id = user.id
        profiles.append(user.userprofile)

    return profiles
