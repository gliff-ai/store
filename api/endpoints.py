# from fastapi import APIRouter, Depends, status, Request
from etebase_fastapi.dependencies import get_authenticated_user
from myauth.models import UserType

# from api import models, schemas

# api_router = APIRouter()

@api_router.get("/")
def hello_world(request: Request, user: UserType = Depends(get_authenticated_user)):
    return {"message": "Hello " + user.email}



# # Users (login and logout are handled by etebase_server and the etebase SDK fe
# @api_router.get("/users/me")
# def me(request: Request, user: UserType = Depends(get_authenticated_user)):
#     return {"email": user.email}
#
# @api_router.put("/users")  # Update a user profile
# def update_profile(request: Request, user: UserType = Depends(get_authenticated_user)):
#     print(user)
#     user.first_name = "craig"
#     user.save()
#     return {"first_name": user.first_name, "email": user.email}
