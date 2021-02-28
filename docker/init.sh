#!/bin/bash

./manage.py migrate
daphne -b 0.0.0.0:8000 YtManager.asgi:application
