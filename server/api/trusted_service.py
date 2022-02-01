from datetime import datetime, timezone
from typing import List
from django.core.exceptions import ObjectDoesNotExist

from ninja import Router

from loguru import logger

from myauth.models import TrustedService, Team, User, UserProfile
from .schemas import (
    TrustedServiceOut,
    TrustedServiceIn,
    Error,
    TrustedServiceCreated,
    TrustedServiceInWithoutId,
)

router = Router()


@router.get("/", response={200: List[TrustedServiceOut], 403: Error})
def get_trusted_service(request):
    user = request.auth

    ts_list = TrustedService.objects.filter(team_id=user.userprofile.team.id)
    return ts_list


@router.post("/", response={200: TrustedServiceCreated, 403: Error, 409: Error, 500: Error})
def create_trusted_service(request, payload: TrustedServiceIn):
    user = request.auth
    team = Team.objects.get(owner_id=user.id)

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can create trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        ts = TrustedService.objects.get(**filter_args)
        if ts is not None:
            return 409, {"message": "Trusted service already exists."}

    except ObjectDoesNotExist as e:
        pass

    try:
        # Get the "user" for the service
        ts_user = User.objects.get(email=payload.id)

        # Create a profile
        user_profile = UserProfile.objects.create(
            user_id=ts_user.id,
            team_id=team.id,
            name=payload.name,
            recovery_key=None,
            accepted_terms_and_conditions=datetime.now(tz=timezone.utc),
            is_collaborator=False,
            is_trusted_service=True,
            email_verified=datetime.now(tz=timezone.utc),
        )
        user_profile.id = user_profile.user_id
        user_profile.email = user.email
        user_profile.save()

        ts = TrustedService.objects.create(
            user_id=ts_user.id,
            type=payload.type,
            name=payload.name,
            url=payload.url,
            team_id=team.id,
            products=payload.products,
            enabled=payload.enabled,
        )

        return {"id": ts.id}
    except Exception as e:
        logger.error(e)


@router.put("/", response={200: TrustedServiceCreated, 403: Error, 500: Error})
def update_trusted_service(request, payload: TrustedServiceInWithoutId):

    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can update trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        ts = TrustedService.objects.get(**filter_args)
        user_profile = ts.user.userprofile
        user_profile.name = payload.name
        ts.name = payload.name
        ts.products = payload.products
        ts.enabled = payload.enabled

        user_profile.save()
        ts.save()
        return {"id": ts.id}
    except Exception as e:
        logger.error(e)


@router.delete("/", response={200: TrustedServiceCreated, 403: Error, 500: Error})
def delete_trusted_service(request, payload: TrustedServiceInWithoutId):

    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can delete trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        ts = TrustedService.objects.get(**filter_args)
        ts_id = ts.id
        ts_user = ts.user
        ts.delete()
        ts_user.delete()
        return {"id": ts_id}
    except Exception as e:
        logger.error(e)
