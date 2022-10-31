from datetime import datetime, timezone
from typing import List
from loguru import logger
from ninja import Router
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from myauth.models import Plugin, TrustedService, User, UserProfile
from .schemas import PluginOutSchema, PluginInSchema, PluginCreatedSchema, PluginDeleteSchema, Error
from .helpers import is_valid_url, edit_plugin, add_plugin, process_plugins


router = Router()


@router.get("/", response={200: List[PluginOutSchema], 403: Error})
def get_plugins(request):
    user = request.auth

    plugins = Plugin.objects.filter(team_id=user.userprofile.team.id)

    return process_plugins(plugins)


@router.get("/zoo/", response={200: List[PluginOutSchema], 403: Error})
def get_zoo_plugins(request):
    user = request.auth

    plugins = Plugin.objects.filter(Q(is_public=True)).exclude(team_id=user.userprofile.team.id)
    excluded_plugin_ids = []  # further exclude all plugins that have already been activated
    for p in plugins:
        try:
            activated_plugin = Plugin.objects.get(Q(team_id=user.userprofile.team.id) & Q(origin_id=p.id))
            if activated_plugin is not None:
                excluded_plugin_ids.append(p.id)

        except ObjectDoesNotExist:
            pass

    plugins = plugins.filter(~Q(id__in=excluded_plugin_ids))

    return process_plugins(plugins)


@router.post("/", response={200: PluginCreatedSchema, 403: Error, 500: Error, 400: Error})
def create_plugin(request, payload: PluginInSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can add plugins."}

    if not is_valid_url(payload.url):
        return 400, {"message": "The URL is invalid."}

    if payload.type != "Javascript" and (
        not hasattr(payload, "username")
        or not hasattr(payload, "public_key")
        or not hasattr(payload, "encrypted_access_key")
    ):
        return 400, {"message": "Missing data in the POST request."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url, "origin_id": payload.origin_id}
        plugin = Plugin.objects.get(**filter_args)
        if plugin is not None:
            return 409, {"message": "Plugin already in use."}
    except ObjectDoesNotExist:
        pass

    try:
        plugin = add_plugin(payload, user.team.id)

        if payload.type == "Python" or payload.type == "AI":
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

                TrustedService.objects.create(
                    user_id=ts_user.id,
                    plugin_id=plugin.id,
                    public_key=payload.public_key,
                    encrypted_access_key=payload.encrypted_access_key,
                )
            except Exception as e:
                logger.error(e)
                plugin.delete()
                return 500, {"message": "Something went wrong"}

        return {"id": plugin.id}
    except Exception as e:
        logger.error(e)


@router.put("/", response={200: PluginCreatedSchema, 403: Error, 500: Error})
def update_plugin(request, payload: PluginInSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can update plugins."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)

        edit_plugin(plugin, payload)

        try:
            ts = TrustedService.objects.get(plugin_id=plugin.id)
            user_profile = ts.user.userprofile
            user_profile.name = payload.name
            user_profile.save()
        except ObjectDoesNotExist:
            pass

        return {"id": plugin.id}
    except Exception as e:
        logger.error(e)


@router.delete("/", response={200: PluginCreatedSchema, 403: Error, 500: Error})
def delete_plugin(request, payload: PluginDeleteSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can delete plugins."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)
        plugin_id = plugin.id
        try:
            ts = TrustedService.objects.get(plugin_id=plugin.id)
            user = ts.user
            logger.info(user.email)
            user.delete()
        except ObjectDoesNotExist:
            pass
        finally:
            plugin.delete()

        return {"id": plugin_id}
    except Exception as e:
        logger.error(e)
