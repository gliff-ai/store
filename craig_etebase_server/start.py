import os
import uvicorn

from django.core.asgi import get_asgi_application
from etebase_fastapi.main import create_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "craig_etebase_server.settings")
django_application = get_asgi_application()

app = create_application()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)