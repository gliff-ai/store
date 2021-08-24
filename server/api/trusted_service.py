from typing import List

from ninja import Router

from myauth.models import TrustedService
from .schemas import TrustedServiceOut, TrustedServiceIn, Error, TrustedServiceCreated

router = Router()


@router.get("/{team_id}", response={200: List[TrustedServiceOut], 403: Error})
def get_trusted_service(request, team_id: int):
    user = request.auth

    if user.userprofile.team_id is not team_id:
        return 403, {"message": "Only team members view the trusted services."}

    ts_list = TrustedService.objects.filter(team_id=team_id)
    return ts_list


@router.post("/", response={200: TrustedServiceCreated, 403: Error, 500: Error})
def create_trusted_service(request, payload: TrustedServiceIn):
    user = request.auth

    if user.userprofile.team_id is not payload.team_id:
        return 403, {"message": "Only owners can create trusted services."}
    ts = TrustedService.objects.create(**payload.dict())
    return {"id": ts.id}
