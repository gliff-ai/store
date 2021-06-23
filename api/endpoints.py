from ninja import NinjaAPI
from ninja.security import APIKeyHeader

from etebase_fastapi.dependencies import get_authenticated_user

from server.api.user import router as users_router
from server.api.tier import router as tiers_router
from server.api.team import router as teams_router
from server.api.billing import router as billing_router

from loguru import logger


class ApiKey(APIKeyHeader):
    param_name = "Authorization"

    def authenticate(self, request, key):
        try:
            if key is None:
                return False

            user = get_authenticated_user(key)  # Validate with Etebase
            return user
        except Exception as e:
            logger.warning(f"Received Exception {e}")
            return False


api = NinjaAPI(auth=ApiKey())


@api.get("/", auth=None)
def healthcheck(request):
    return "Hello World"


api.add_router("/tier", tiers_router)
api.add_router("/user", users_router)
api.add_router("/team", teams_router)
api.add_router("/billing", billing_router)
