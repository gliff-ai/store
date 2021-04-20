from fastapi import APIRouter
from fastapi import APIRouter, Depends, status, Request
from fastapi.security.api_key import APIKeyHeader

from etebase_fastapi.dependencies import get_authenticated_user
from myauth.models import UserType

# from api import models, schemas


api_router = APIRouter()

@api_router.get("/")
def hello_world(request: Request, user: UserType = Depends(get_authenticated_user)):
    return {"message": "Hello " + user.email}