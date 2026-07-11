#!/bin/sh
# запуск на amvera: миграции и статика на старте, дальше gunicorn
set -e
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py createsuperuser --noinput || true
exec gunicorn config.wsgi:application --bind 0.0.0.0:80
