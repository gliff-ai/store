# These are mounted under /django
import os

from loguru import logger
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.contrib.staticfiles import finders
from ninja import NinjaAPI
from ninja.security import APIKeyHeader
from etebase_fastapi.dependencies import get_authenticated_user

from .api.user import router as users_router
from .api.tier import router as tiers_router
from .api.team import router as teams_router
from .api.project import router as project_router
from .api.billing import router as billing_router
from .api.plugin import router as plugin_router
from .api.sentry import router as sentry_router
from .api.feedback import router as feedback_router


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
    if settings.TEST_MODE:
        return "Hello Test World"
    else:
        return "Hello World"


api.add_router("/tier", tiers_router)
api.add_router("/user", users_router)
api.add_router("/team", teams_router)
api.add_router("/billing", billing_router)
api.add_router("/project", project_router)
api.add_router("/tunnel", sentry_router)
api.add_router("/plugin", plugin_router)
api.add_router("/feedback", feedback_router)


urlpatterns = [
    url(r"^admin/", admin.site.urls),
    path("api/", api.urls),
]


if settings.DEBUG:

    def serve_static(request, path):
        filename = finders.find(path)
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)

        return serve(request, basename, dirname)

    urlpatterns += [re_path(r"^static/(?P<path>.*)$", serve_static)]
