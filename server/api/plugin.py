from typing import List
from loguru import logger
from ninja import Router
from myauth.models import Plugin
from .schemas import PluginOut, PluginSchema, PluginCreated, PluginIn, Error
from django.core.exceptions import ObjectDoesNotExist
from .helpers import is_valid_url, get_author, add_plugin, process_collection_uids


router = Router()


@router.get("/", response={200: List[PluginOut], 403: Error})
def get_plugins(request):
    user = request.auth

    filter_args = {"team_id": user.userprofile.team.id, "type": "Javascript"}
    plugins = Plugin.objects.filter(**filter_args)
    for p in plugins:
        p.author = get_author(p)
        p.collection_uids = p.collections.values_list("uid", flat=True)

    return plugins


@router.post("/", response={200: PluginCreated, 403: Error, 500: Error, 400: Error})
def create_plugin(request, payload: PluginIn):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can add plugins."}

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
        plugin_id = add_plugin(payload, user.team.id)
        return {"id": plugin_id}
    except Exception as e:
        logger.error(e)


@router.put("/", response={200: PluginCreated, 403: Error, 500: Error})
def update_plugin(request, payload: PluginSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can update plugins."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)

        plugin.name = payload.name
        plugin.description = payload.description
        plugin.products = payload.products
        plugin.enabled = payload.enabled
        plugin.save()

        process_collection_uids(plugin, payload.collection_uids)

        return {"id": plugin.id}
    except Exception as e:
        logger.error(e)


@router.delete("/", response={200: PluginCreated, 403: Error, 500: Error})
def delete_plugin(request, payload: PluginSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can delete plugins."}

    try:
        filter_args = {"team_id": user.userprofile.team.id, "url": payload.url}
        plugin = Plugin.objects.get(**filter_args)
        plugin_id = plugin.id
        plugin.delete()
        return {"id": plugin_id}
    except Exception as e:
        logger.error(e)
