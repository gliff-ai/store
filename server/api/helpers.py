from loguru import logger
from typing import List, Dict, Union
from myauth.models import Plugin, TrustedService
from .schemas import PluginInSchema
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import URLValidator
from django_etebase.models import Collection, CollectionMember


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


def process_plugins(plugins: List[Plugin]) -> List[Plugin]:
    for p in plugins:
        if p is not None:
            p.author = get_author(p)
            if p.type == "Javascript":
                p.collection_uids = p.collections.values_list("uid", flat=True)

            if p.type == "Python" or p.type == "AI":
                ts = TrustedService.objects.get(plugin_id=p.id)

                current_collections = CollectionMember.objects.filter(user__email=ts.user.email).values_list(
                    "collection__uid", flat=True
                )
                p.collection_uids: List[Dict[str, Union[str, bool]]] = [
                    {"uid": uid, "is_invite_pending": uid not in current_collections}
                    for uid in p.collections.values_list("uid", flat=True)
                ]
                p.username = ts.user.username
                p.public_key = ts.public_key
                p.encrypted_access_key = ts.encrypted_access_key

    return plugins


def add_plugin(payload: PluginInSchema, team_id: int) -> Plugin:
    is_origin = payload.origin_id is None
    plugin = Plugin.objects.create(
        team_id=team_id,
        name=payload.name,
        type=payload.type,
        description=payload.description,
        url=payload.url,
        products=payload.products,
        enabled=payload.enabled if is_origin else True,
        is_public=payload.is_public if is_origin else None,
    )
    plugin.origin_id = plugin.id if payload.origin_id is None else payload.origin_id
    plugin.save()

    process_collection_uids(plugin, payload.collection_uids)
    return plugin


def edit_plugin(plugin: Plugin, payload: PluginInSchema) -> None:
    plugin.name = payload.name
    plugin.description = payload.description
    plugin.products = payload.products
    plugin.enabled = payload.enabled
    plugin.is_public = payload.is_public
    plugin.save()

    process_collection_uids(plugin, payload.collection_uids)


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
