# Blocklist for endpoints collaborators can't use.
# There might be nicer ways but this also lets us block mounted etebase routes
# Also there might be overlap as some of these would be blocked anyway as the user isn't a team owner
from loguru import logger
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send

from .helpers import get_key_from_headers, get_user_is_collab


class EnforceCollabMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # [(Method, Path)]
        routes = [
            ("POST", "/api/v1/collection"),  # Create Collection
            ("POST", "/django/api/invite"),  # Invite User
            ("GET", "/django/api/team"),  # View team
            ("*", "/django/api/billing"),  # Any billing routes
        ]

        # Explicit Allow
        if scope["path"].startswith("/django/api/billing/create-checkout-session") or scope["path"].startswith(
            "/django/api/billing/webhook"
        ):
            await self.app(scope, receive, send)
            return

        # Allow CORS requests
        if scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        for (method, path) in routes:
            if (method == scope["method"] or method == "*") and scope["path"].startswith(path):
                # This runs before our regular auth, so we have to check here
                key = get_key_from_headers(scope["headers"])
                is_collab = await get_user_is_collab(key)
                if is_collab:
                    logger.info("Blocked by EnforceCollabMiddleware")
                    response = JSONResponse({"message": "Collaborators can't access this"}, status_code=401)
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
