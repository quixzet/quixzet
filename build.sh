#!/usr/bin/env bash
# Сборка на Render: зависимости, статика, миграции
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Каталог из catalog.json — только в пустую базу, чтобы не затирать правки из админки
if ! python manage.py shell -c "from app.models import Product; raise SystemExit(0 if Product.objects.exists() else 1)"; then
    python manage.py loaddata catalog.json
fi

# Админ из переменных DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD (если заданы и его ещё нет)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --no-input || true
fi
