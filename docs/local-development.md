# Локальная разработка

## Требования

- Python 3.14 и `uv`;
- Node.js 22 или новее и npm;
- PostgreSQL;
- Redis.

## Backend

Создайте окружение и установите зависимости:

```bash
cp .env_example .env
uv sync --frozen
```

Проверьте `DB_*`, `REDIS_URL`, `CELERY_BROKER_URL` и `CACHE_URL` в `.env`, затем
выполните миграции и создайте администратора:

```bash
.venv/bin/python app/manage.py migrate
.venv/bin/python app/manage.py createsuperuser
.venv/bin/python app/manage.py runserver
```

Backend будет доступен на `http://127.0.0.1:8000`.

## Celery

Обычный worker без `--queues` слушает все три очереди проекта:

```bash
cd app
../.venv/bin/celery -A config worker --loglevel=INFO
```

Планировщик запускается отдельно:

```bash
cd app
../.venv/bin/celery -A config beat --loglevel=INFO
```

## Frontend

```bash
cd frontend
npm ci
npm run dev
```

Vite работает на `http://127.0.0.1:5173` и проксирует `/api` в Django на
`http://127.0.0.1:8000`.

## Почта

Для разработки можно переключить backend на консольный:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Для проверки настоящего SMTP заполните параметры из `.env_example`. Не
добавляйте пароль приложения или пароль почтового ящика в Git.

## Проверки

```bash
.venv/bin/python app/manage.py check
.venv/bin/python app/manage.py test
cd frontend && npm run lint && npm run test:e2e
```

Тестовый runner автоматически находит приложения `accounts`, `promo`, `draws`
и `core`. Для backend-тестов нужна доступная PostgreSQL с правом создавать
тестовую базу. Celery в тестах работает eagerly и не требует Redis.
