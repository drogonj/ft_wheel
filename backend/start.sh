#!/bin/sh

mkdir django/staticfiles
python3 django/manage.py collectstatic --noinput
echo ""
python3 django/manage.py makemigrations
echo ""
python3 django/manage.py migrate
echo ""

python3 django/create_superusers.py
echo ""
python3 django/create_authorized_external_users.py
echo ""


export PYTHONPATH="/backend/django"

daphne -b 0.0.0.0 -p 8000 luckywheel.asgi:application