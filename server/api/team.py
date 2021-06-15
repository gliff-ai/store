from typing import List

from ninja import Router

from myauth.models import UserProfile, Tier, Team, User, Invite
from .schemas import UserProfileOut, InvitedProfileOut, TeamsOut

router = Router()


@router.get(
    "/",
    response=TeamsOut,
)
def get_team(request):
    user = request.auth

    # is the user the owner of the team?
    user.userprofile.id = user.id

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can view the team"}

    users = User.objects.filter(userprofile__team__owner_id=user.id)

    profiles = []
    for u in users:
        u.userprofile.id = u.id
        u.userprofile.email = u.email
        profiles.append(u.userprofile)

    # Add invited, but not accepted users
    invites = Invite.objects.filter(
        from_team_id=user.team.id, accepted_date=None
    ).values("email", "sent_date")

    return {"profiles": profiles, "pending_invites": list(invites)}
