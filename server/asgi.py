import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")
django_application = get_asgi_application()

def create_app():
    from etebase_fastapi.main import create_application
    app = create_application()
    app.mount("/etebase", django_application)

    return app


application = create_app()
