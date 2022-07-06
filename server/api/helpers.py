from loguru import logger
from myauth.models import Plugin
from .schemas import PluginIn
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import URLValidator
from django_etebase.models import Collection


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


def add_plugin(payload: PluginIn, team_id: int) -> int:
    plugin = Plugin.objects.create(
        team_id=team_id,
        name=payload.name,
        type=payload.type,
        description=payload.description,
        url=payload.url,
        products=payload.products,
        enabled=payload.enabled,
    )
    plugin.origin_id = plugin.id if payload.origin_id is None else payload.origin_id
    plugin.save()

    process_collection_uids(plugin, payload.collection_uids)
    return plugin.id


def get_author(plugin: Plugin) -> str:
    return plugin.team.name if plugin.origin is None else plugin.origin.team.name


def is_valid_url(url):
    validator = URLValidator()
    try:
        validator(url)
        return True
    except ValidationError as e:
        logger.warning(f"Received ValidationError: {e}")
        return False
