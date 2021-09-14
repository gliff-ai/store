from typing import List

from ninja import Router

from myauth.models import Plugin
from .schemas import PluginOut, PluginIn, PluginCreated, Error
from loguru import logger

router = Router()


@router.get("/{team_id}", response={200: List[PluginOut], 403: Error})
def get_plugins(request, team_id: int):
    user = request.auth

    if user.userprofile.team_id is not team_id:
        return 403, {"message": "Only team members can view plugins."}

    filter_args = {"teams__id": team_id, "enabled": True}
    plugins_list = Plugin.objects.filter(**filter_args)
    return plugins_list


@router.post("/", response={200: PluginCreated, 403: Error, 500: Error})
def create_plugin(request, payload: PluginIn):
    user = request.auth

    if user.userprofile.team_id is not payload.team_id:
        return 403, {"message": "Only owners can add plugins."}

    try:
        plugin = Plugin.objects.create(url=payload.url, product=payload.product)
        logger.info(plugin)
        plugin.teams.add(user.userprofile.team)
        plugin.save()
        return {"id": plugin.id}
    except Exception as e:
        logger.error(e)
