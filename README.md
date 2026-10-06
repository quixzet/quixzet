# QUIXZET

Магазин одежды на Django. Без лишнего. Без компромиссов.

Монохромный бруталистский дизайн, каталог с фильтрами, корзина, оформление и оплата заказа (имитация), личный кабинет с заказами и адресами, 3D-просмотр товаров с AR на телефоне.

## Стек

- Python 3.14, Django 6.1, django-environ, Pillow
- SQLite по умолчанию, PostgreSQL — через `DATABASE_URL`
- Вёрстка — шаблоны Django + свой CSS и JS без фреймворков
- 3D — [`<model-viewer>`](https://modelviewer.dev) с декодером meshopt, оба файла лежат в `app/static/js/vendor/`

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env    # и вписать свой DJANGO_SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Сайт — http://127.0.0.1:8000, админка — http://127.0.0.1:8000/admin.

Сгенерировать секретный ключ:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Товары и фото

Товары, варианты (размер / цвет / цена / остаток) и фото добавляются в админке.
Фото лучше загружать от 1200–1600 px по высоте — на больших экранах маленькие выглядят мыльно.

## 3D-модели

У товара есть поле «3D-модель» (`.glb`). Сырые модели из сканов и нейросетей весят десятки мегабайт — перед загрузкой их стоит сжать:

```powershell
npx @gltf-transform/cli optimize model.glb model-web.glb --compress meshopt --simplify-ratio 0.08 --simplify-error 0.002 --texture-compress false
```

В репозиторий попадают только сжатые модели (`*-web.glb`), исходники — нет (см. `.gitignore`).

## Структура

```
app/
  models.py, views.py, selectors.py   каталог, корзина, заказы, профиль
  templatetags/qx.py                  цены «29 990 ₽», склонения, скидки
  context_processors.py               счётчик корзины в шапке
  templates/                          страницы и партиалы
  static/css/base.css                 все стили (слои, токены, тёмная тема)
  static/js/base.js                   интерактив: карусель, модалки, бегущие строки
project/                              настройки Django
media/                                фото товаров и 3D-модели
```
