from typing import List
from ninja import Router

from myauth.models import Tier
from .schemas import TierSchema

router = Router()


@router.get("/tier", response=List[TierSchema], auth=None)
def list_tiers(request):
    return Tier.objects.all()
