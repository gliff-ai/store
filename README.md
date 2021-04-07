```bash
python manage.py migrate

uvicorn craig_etebase_server.asgi:application --host 0.0.0.0 --port 8033 --log-level trace --reload
```
