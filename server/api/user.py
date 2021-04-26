from ninja import Router

from myauth.models import UserProfile, Tier, Team
from .schemas import UserProfileIn, UserProfileOut, Error

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
        # TODO  We need a way to check they have been invited to a team, otherwise you could join any team
        team = Team.objects.get(id=payload.team_id)

    UserProfile.objects.create(
        user_id=user.id,
        team_id=team.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        recovery_key=payload.recovery_key,
    )

    user.save()
    return user.userprofile


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
