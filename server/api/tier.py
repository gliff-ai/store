from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router

from myauth.models import Tier
from .schemas import TierSchema

router = Router()


@router.get("/", response=List[TierSchema], auth=None)
def list_tiers(request):
    return Tier.objects.all()


@router.get("/{tier_id}", response=TierSchema)
def get_tier(request, tier_id: int):
    tier = get_object_or_404(Tier, id=tier_id)
    return tier
