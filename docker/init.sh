#!/bin/sh

./manage.py migrate --noinput
./manage.py collectstatic --noinput
#daphne -b 0.0.0.0 -p 8000 YtManager.asgi:application
#gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 YtManager.asgi:application
uvicorn YtManager.asgi:application --host 0.0.0.0 --port 8000
