from typing import List

from ninja import Router

from django.shortcuts import get_object_or_404
from myauth.models import TrustedService
from .schemas import TrustedServiceSchema, Error, TrustedServiceCreated

router = Router()


@router.get("/", response=List[TrustedServiceSchema], auth=None)
def list_trusted_services(request):
    return TrustedService.objects.all()


@router.get("/{trusted_service_id}", response=TrustedServiceSchema, auth=None)
def get_employee(request, trusted_service_id: int):
    trusted_service = get_object_or_404(TrustedService, id=trusted_service_id)
    return trusted_service


@router.post("/", response={200: TrustedServiceCreated, 500: Error}, auth=None)
def create_trusted_service(request, trusted_service: TrustedServiceSchema):
    trusted_service = TrustedService.objects.create(**trusted_service.dict())
    return {"id": trusted_service.id}
