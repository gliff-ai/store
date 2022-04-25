from ninja import Router
from loguru import logger

from myauth.models import User, Invite
from .schemas import TeamsOut, Error

router = Router()


@router.get(
    "/",
    response={200: TeamsOut, 403: Error},
)
def get_team(request):
    user = request.auth

    if user.userprofile.is_collaborator or user.userprofile.is_trusted_service:
        return 403, {"message": "Only owners or members can view the team"}

    users = User.objects.filter(userprofile__team__owner_id=user.userprofile.team.owner)

    profiles = []
    for u in users:
        u.userprofile.id = u.id
        u.userprofile.email = u.email
        profiles.append(u.userprofile)

    # Add invited, but not accepted users
    invites = Invite.objects.filter(from_team_id=user.userprofile.team.id, accepted_date=None).values(
        "email", "sent_date", "is_collaborator"
    )

    # We send trusted services as users too and filter them frontend

    return {"profiles": profiles, "pending_invites": list(invites), "owner": user.userprofile.team.owner}
