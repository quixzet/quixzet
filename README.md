# QUIXZET

Магазин одежды с каталогом, фильтрами, корзиной, личным кабинетом и 3D-просмотром товаров.

- Django на Python 3.14 обслуживает JSON API на `/api/`, админку на `/admin/` и загруженные медиафайлы на `/media/`. По умолчанию используется SQLite. Переменная `DATABASE_URL` позволяет подключить PostgreSQL.
- Node.js 22+ в `frontend/` самостоятельно отдаёт страницы, стили и скрипты. Express обращается к Django через `BACKEND_URL` и передаёт браузеру сессионную cookie Django. Фронтенд можно запускать на другом сервере, если он может подключиться к API.

## Локальный запуск

В корне репозитория создайте виртуальное окружение, установите зависимости и скопируйте `.env.example` в `.env`. Задайте случайный `DJANGO_SECRET_KEY`.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py loaddata catalog.json
python manage.py createsuperuser
python manage.py runserver
```

В PowerShell активируйте окружение командой `.venv\Scripts\Activate.ps1` и скопируйте файл командой `Copy-Item .env.example .env`.

В другом терминале из корня репозитория:

```sh
cd frontend
npm ci
npm start
```

Витрина доступна по адресу http://127.0.0.1:3000, админка — http://127.0.0.1:8000/admin/, каталог API — http://127.0.0.1:8000/api/.

Для других адресов настройте `frontend/.env`, укажите хост Django в `ALLOWED_HOSTS` и добавьте публичный origin витрины к `CSRF_TRUSTED_ORIGINS`. В рабочем окружении используйте HTTPS и `DEBUG=False`. Если Django стоит за прокси, включайте `TRUST_PROXY_SSL_HEADER` только когда прокси подставляет свой `X-Forwarded-Proto` и удаляет одноимённый заголовок клиента. Статику админки собирает `python manage.py collectstatic --noinput`. Для медиа настройте раздачу `/media/` рядом с Django либо задайте `SERVE_MEDIA=True`.

Товары, размеры, остатки и фотографии редактируются в админке. Для 3D-просмотра загрузите сжатый файл `.glb`. Оплата в магазине имитируется.
