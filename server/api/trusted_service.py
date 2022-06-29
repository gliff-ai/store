from datetime import datetime, timezone
from typing import List
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import URLValidator

from ninja import Router

from loguru import logger

from myauth.models import TrustedService, Plugin, User, UserProfile
from django_etebase.models import Collection
from .schemas import (
    TrustedServiceOut,
    TrustedServiceSchema,
    TrustedServiceCreated,
    Error,
)

router = Router()


def process_collection_uids(model, collection_uids):
    if collection_uids is not None:
        model.collections.clear()
        for uid in collection_uids:
            try:
                collection = Collection.objects.get(uid=uid)
                model.collections.add(collection)

            except ObjectDoesNotExist:
                logger.error(f"Project {uid} does not exist.")
        model.save()


def is_valid_url(url):
    validator = URLValidator()
    try:
        validator(url)
        return True
    except ValidationError as e:
        logger.warning(f"Received ValidationError: {e}")
        return False


@router.get("/", response={200: List[TrustedServiceOut], 403: Error})
def get_trusted_service(request):
    user = request.auth

    plugins = Plugin.objects.filter(team_id=user.userprofile.team.id).exclude(type="Javascript")

    for p in plugins:
        p.collection_uids = p.collections.values_list("uid", flat=True)
        ts = TrustedService.objects.get(plugin_id=p.id)
        p.username = ts.user.username
    return plugins


@router.post("/", response={200: TrustedServiceCreated, 403: Error, 409: Error, 500: Error, 400: Error})
def create_trusted_service(request, payload: TrustedServiceSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can create trusted services."}

    if not is_valid_url(payload.url):
        return 400, {"message": "The URL is invalid."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)
        if plugin is not None:
            return 409, {"message": "Plugin already exists."}

    except ObjectDoesNotExist:
        pass

    try:
        # Get the "user" for the service
        ts_user = User.objects.get(email=payload.username)

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
            author=user.team.name,
            name=payload.name,
            description=payload.description,
            url=payload.url,
            products=payload.products,
            enabled=payload.enabled,
        )

        process_collection_uids(plugin, payload.collection_uids)

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
        plugin.description = payload.description
        plugin.products = payload.products
        plugin.enabled = payload.enabled
        plugin.save()

        process_collection_uids(plugin, payload.collection_uids)

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
        ts_user = User.objects.get(email=payload.username)
        ts = TrustedService.objects.get(user_id=ts_user.id)
        ts_id = ts.id
        ts.plugin.delete()
        ts.user.delete()
        return {"id": ts_id}
    except Exception as e:
        logger.error(e)
