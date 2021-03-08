#!/bin/sh

./manage.py migrate --noinput
./manage.py collectstatic --noinput
daphne -b 0.0.0.0 -p 8000 YtManager.asgi:application
