import os
import uvicorn
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

django.setup()

from django.core.asgi import get_asgi_application
from etebase_fastapi.main import create_application

if __name__ == "__main__":
    django_application = get_asgi_application()

    app = create_application()
    uvicorn.run(app, host="0.0.0.0", port=8033)