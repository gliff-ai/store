import os
import uvicorn
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")

django.setup()

from django.core.asgi import get_asgi_application
from etebase_fastapi.main import create_application

from fastapi import APIRouter, Depends, status, Request
from fastapi.security.api_key import APIKeyHeader

from etebase_fastapi.dependencies import get_authenticated_user
from myauth.models import UserType

token_scheme = APIKeyHeader(name="Authorization")

if __name__ == "__main__":
    django_application = get_asgi_application()

    app = create_application()

    @app.get("/")
    def root(request: Request, user: UserType = Depends(get_authenticated_user)):
        return {"message": "Hello " + user.email}

    uvicorn.run(app, host="0.0.0.0", port=8000)

