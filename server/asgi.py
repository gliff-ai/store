import os
import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI
from etebase_fastapi.main import create_application
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")
django.setup()


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

    # We mount Django (and the API, via urls.py) under /django
    app.mount("/django", WSGIMiddleware(get_wsgi_application()))

    # All the etebase api routes are here
    app.mount("/etebase", etebase_app)

    return app


app = get_application()
