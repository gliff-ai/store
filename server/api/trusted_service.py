from datetime import datetime, timezone
from typing import List
from django.core.exceptions import ObjectDoesNotExist

from ninja import Router

from loguru import logger

from myauth.models import TrustedService, Plugin, Team, User, UserProfile
from .schemas import (
    TrustedServiceSchema,
    ExtendedTrustedServiceSchema,
    TrustedServiceCreated,
    Error,
)

router = Router()


@router.get("/", response={200: List[TrustedServiceSchema], 403: Error})
def get_trusted_service(request):
    user = request.auth

    ts_list = Plugin.objects.filter(team_id=user.userprofile.team.id).exclude(type="Javascript")
    return ts_list


@router.post("/", response={200: TrustedServiceCreated, 403: Error, 409: Error, 500: Error})
def create_trusted_service(request, payload: ExtendedTrustedServiceSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can create trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)
        if plugin is not None:
            return 409, {"message": "Plugin already exists."}

    except ObjectDoesNotExist as e:
        pass

    try:
        # Get the "user" for the service
        ts_user = User.objects.get(email=payload.id)

        # Create a profile
        user_profile = UserProfile.objects.create(
            user_id=ts_user.id,
            team_id=user.team.id,
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

        plugin = Plugin.objects.create(
            team_id=user.team.id,
            type=payload.type,
            name=payload.name,
            url=payload.url,
            products=payload.products,
            enabled=payload.enabled,
        )

        ts = TrustedService.objects.create(
            user_id=ts_user.id,
            plugin_id=plugin.id,
        )

        return {"id": ts.id}
    except Exception as e:
        logger.error(e)


@router.put("/", response={200: TrustedServiceCreated, 403: Error, 500: Error})
def update_trusted_service(request, payload: TrustedServiceSchema):

    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can update trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)

        plugin.name = payload.name
        plugin.products = payload.products
        plugin.enabled = payload.enabled
        plugin.save()

        ts = TrustedService.objects.get(plugin_id=plugin.id)
        user_profile = ts.user.userprofile
        user_profile.name = payload.name
        user_profile.save()

        return {"id": ts.id}
    except Exception as e:
        logger.error(e)


@router.delete("/", response={200: TrustedServiceCreated, 403: Error, 500: Error})
def delete_trusted_service(request, payload: TrustedServiceSchema):

    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can delete trusted services."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)
        ts = TrustedService.objects.get(plugin_id=plugin.id)
        ts_id = ts.id
        ts_user = ts.user
        plugin.delete()
        ts_user.delete()
        return {"id": ts_id}
    except Exception as e:
        logger.error(e)
