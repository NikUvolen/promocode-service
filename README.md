# Gear Drop

[![Documentation](https://github.com/NikUvolen/promocode-service/actions/workflows/docs-pages.yml/badge.svg)](https://github.com/NikUvolen/promocode-service/actions/workflows/docs-pages.yml)

Gear Drop — платформа промоакции для игровых устройств. Участник создает
аккаунт, подтверждает email, заполняет профиль и регистрирует уникальные
восьмизначные промокоды. Каждый день разыгрываются два приза, а результаты
публикуются на лендинге.

## Возможности

- регистрация, подтверждение email, вход и восстановление пароля;
- JWT в HttpOnly cookies и blacklist refresh-токенов;
- обязательное заполнение профиля перед регистрацией промокода;
- защита ввода кодов: три ошибки за минуту и блокировка на пять минут;
- ежедневные и ручные идемпотентные розыгрыши;
- ограничение на одну победу пользователя за всю акцию;
- письма о регистрации кода и обязательные письма победителям;
- XLSX-импорт, генерация кодов и отчеты в Django admin;
- отдельные Celery-очереди для розыгрышей, уведомлений и тяжелых задач;
- журнал аудита, восстановление зависших задач и автоматическая очистка;
- OpenAPI-схема и Swagger UI.

## Стек

| Область | Технологии |
| --- | --- |
| Backend | Python 3.14, Django 6.1, Django REST Framework |
| Frontend | React 19, Vite 8, React Router |
| Данные | PostgreSQL 17, Redis 8 |
| Фоновые задачи | Celery 5, Celery Beat |
| Админка | Django Unfold |
| Production | Docker Compose, Gunicorn, Nginx |

## Быстрый запуск в Docker

1. Создайте файл окружения:

   ```bash
   cp .env.production.example .env.production
   ```

2. Замените примерные секреты и адреса. Значения `DB_*` и `POSTGRES_*` должны
   описывать одни и те же учетные данные.

3. Запустите stack:

   ```bash
   docker compose -p gear-drop --env-file .env.production up -d --build
   ```

4. Создайте администратора:

   ```bash
   docker compose -p gear-drop --env-file .env.production \
     exec backend python manage.py createsuperuser
   ```

Frontend будет доступен на `http://127.0.0.1:8080/`, Django admin — на
`http://127.0.0.1:8080/admin/`, Swagger UI — на
`http://127.0.0.1:8080/api/docs/`.

## Локальная разработка

Для backend нужны PostgreSQL, Redis, Python 3.14 и `uv`.

```bash
cp .env_example .env
uv sync --frozen
.venv/bin/python app/manage.py migrate
.venv/bin/python app/manage.py runserver
```

В другом терминале запустите Celery. Локальный worker без `--queues` слушает
все объявленные очереди:

```bash
cd app
../.venv/bin/celery -A config worker --loglevel=INFO
../.venv/bin/celery -A config beat --loglevel=INFO
```

Frontend запускается из каталога `frontend/`:

```bash
npm ci
npm run dev
```

## Тесты

```bash
.venv/bin/python app/manage.py test
cd frontend && npm run lint && npm run test:e2e
```

Backend-тесты используют отдельную тестовую базу PostgreSQL и выполняют Celery
tasks в eager-режиме без Redis. Playwright самостоятельно запускает Vite.

## Документация

Полная документация хранится как Diplodoc-проект в [`docs/`](docs/) и
публикуется в [GitHub Pages](https://nikuvolen.github.io/promocode-service/).
Перед первой публикацией выберите в настройках репозитория **Settings → Pages →
Source: GitHub Actions**.

Локальная сборка требует Node.js 22 или новее:

```bash
npx --yes @diplodoc/cli@5.50.6 -i docs -o _site --strict
```

Инструкция по production-развертыванию также доступна в [DEPLOY.md](DEPLOY.md).

## Структура репозитория

```text
app/                 Django-проект и приложения
frontend/            React/Vite клиент
deploy/              production-конфигурация Nginx
docs/                исходники Diplodoc
.github/workflows/   публикация GitHub Pages
compose.yaml         production Docker Compose stack
```
