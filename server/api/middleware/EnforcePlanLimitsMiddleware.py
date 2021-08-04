from loguru import logger
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send

from .helpers import get_key_from_headers, get_team_limits


class EnforcePlanLimitsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        routes = ["/api/v1/collection", "/django/api/user/invite"]

        # Do we care about this route?
        if scope["method"] != "POST" or (not any(scope["path"].startswith(route) for route in routes)):
            await self.app(scope, receive, send)
            return

        key = get_key_from_headers(scope["headers"])
        team_limits = await get_team_limits(key)

        response = None

        # Projects
        if scope["path"].startswith("/api/v1/collection") and team_limits["projects_limit"] is not None:
            if team_limits["projects_limit"] >= team_limits["projects"]:
                logger.info("Can't create a new project")
                response = JSONResponse({"message": "Can't create a new project"}, status_code=401)

        # Users
        if scope["path"].startswith("/django/api/user/invite") and team_limits["users_limit"] is not None:
            if team_limits["users_limit"] >= team_limits["users"]:
                logger.info("Can't invite a new user")
                response = JSONResponse({"message": "Can't invite a new user"}, status_code=401)

        # Collabs
        if (
            scope["path"].startswith("/django/api/user/invite/collaborator")
            and team_limits["collaborators_limit"] is not None
        ):
            if team_limits["collaborators_limit"] >= team_limits["collaborators"]:
                logger.info("Can't invite a new collaborator")
                response = JSONResponse({"message": "Can't invite a new collaborator"}, status_code=401)

        if response is not None:
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
