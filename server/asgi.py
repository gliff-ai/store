import os
import django
from loguru import logger
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from etebase_fastapi.dependencies import get_authenticated_user
from fastapi import FastAPI, HTTPException
from etebase_fastapi.main import create_application
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send, ASGIApp

from server.api.billing import calculate_limits

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")
django.setup()


@sync_to_async()
def get_team_limits(key):
    user = get_authenticated_user(key)
    return calculate_limits(user.team)


class TempMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send, *args) -> None:
        routes = ["/api/v1/collection/", "/django/api/invite/"]

        # Do we care about this route?
        if scope["path"] not in routes or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        headers = scope["headers"]

        key = [v[1].decode("utf-8") for i, v in enumerate(headers) if v[0] == b"authorization"].pop()
        team_limits = await get_team_limits(key)

        response = None

        # Projects
        if scope["path"] == "/api/v1/collection/" and team_limits["projects_limit"] is not None:
            if team_limits["projects_limit"] >= team_limits["projects"]:
                logger.info("Can't create a new project")
                response = JSONResponse({"message": "Can't create a new project"}, status_code=401)

        # Users & Collabs
        if scope["path"] == "/django/api/invite/" and team_limits["users_limit"] is not None:
            # TODO are they adding a user or a collaborator
            if team_limits["users_limit"] >= team_limits["users"]:
                logger.info("Can't invite a new user")
                response = JSONResponse({"message": "Can't invite a new user"}, status_code=401)

        if response is not None:
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def get_application() -> FastAPI:
    etebase_app = create_application(middlewares=[TempMiddleware])

    app = FastAPI(title="STORE", debug=settings.DEBUG)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TempMiddleware)

    # We mount Django (and the API, via urls.py) under /django
    app.mount("/django", WSGIMiddleware(get_wsgi_application()))

    # All the etebase api routes are here
    app.mount("/etebase", etebase_app)

    return app


app = get_application()
