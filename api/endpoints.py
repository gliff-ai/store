from ninja import NinjaAPI
from ninja.security import APIKeyHeader

from etebase_fastapi.dependencies import get_authenticated_user

from server.api.user import router as users_router
from server.api.tier import router as tiers_router


class ApiKey(APIKeyHeader):
    param_name = "Authorization"

    def authenticate(self, request, key):
        user = get_authenticated_user(key)  # Validate with Etebase
        return user


api = NinjaAPI(auth=ApiKey())


@api.get("/", auth=None)
def healthcheck(request):
    return "Hello World"


api.add_router("/tier", tiers_router)
api.add_router("/user", users_router)
