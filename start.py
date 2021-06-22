import os
import uvicorn
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings.base")

django.setup()

from server.asgi import get_application

if __name__ == "__main__":
    app = get_application()
    uvicorn.run(app, host="0.0.0.0", port=8000)
