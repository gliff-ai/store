import os
import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")
django.setup()

from fastapi import FastAPI
from etebase_fastapi.main import create_application
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware

from api.endpoints import api_router

def get_application() -> FastAPI:
    etebase_app = create_application()

    app = FastAPI(title="STORE", debug=settings.DEBUG)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.mount("/django", WSGIMiddleware(get_wsgi_application()))
    app.mount("/etebase", etebase_app)

    return app


app = get_application()
