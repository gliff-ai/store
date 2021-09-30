from typing import List

from ninja import Router

from myauth.models import Plugin
from .schemas import PluginSchema, PluginCreated, Error
from loguru import logger

router = Router()


@router.get("/", response={200: List[PluginSchema], 403: Error})
def get_plugins(request):
    user = request.auth

    filter_args = {"teams__id": user.userprofile.team.id, "enabled": True}
    plugins_list = Plugin.objects.filter(**filter_args)
    return plugins_list


@router.post("/", response={200: PluginCreated, 403: Error, 500: Error})
def create_plugin(request, payload: PluginSchema):
    user = request.auth

    if user.team.owner_id is not user.id:
        return 403, {"message": "Only owners can add plugins."}

    try:
        plugin = Plugin.objects.create(url=payload.url, product=payload.product)
        plugin.teams.add(user.team)
        plugin.save()
        return {"id": plugin.id}
    except Exception as e:
        logger.error(e)
