# Развертывание

Production stack является отдельным Docker Compose project с именем
`gear-drop`. Он публикует Nginx на порту `8080`, а PostgreSQL и Redis доступны
только внутри compose-сети проекта.

## Подготовка

```bash
git clone https://github.com/NikUvolen/promocode-service.git /opt/gear-drop
cd /opt/gear-drop
cp .env.production.example .env.production
chmod 600 .env.production
```

Замените все примерные секреты. `DB_*` и `POSTGRES_*` должны описывать одни и те
же учетные данные. Для доступа по IP укажите `SERVER_IP` в
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` и `FRONTEND_URL`.

## Первый запуск

```bash
docker compose -p gear-drop --env-file .env.production \
  up -d --build --remove-orphans
docker compose -p gear-drop --env-file .env.production \
  exec backend python manage.py createsuperuser
```

Проверка:

```bash
docker compose -p gear-drop --env-file .env.production ps
curl http://127.0.0.1:8080/health/
```

Адреса сервиса:

- frontend: `http://SERVER_IP:8080/`;
- admin: `http://SERVER_IP:8080/admin/`;
- Swagger UI: `http://SERVER_IP:8080/api/docs/`.

## Обновление

```bash
cd /opt/gear-drop
git pull --ff-only
docker compose -p gear-drop --env-file .env.production \
  up -d --build --remove-orphans
```

## Диагностика

```bash
docker compose -p gear-drop --env-file .env.production ps
docker compose -p gear-drop --env-file .env.production \
  logs --tail=200 backend web worker-critical worker-notifications worker-bulk beat
```

Не выполняйте `docker compose down -v`, если данные PostgreSQL, Redis и media
нужно сохранить. Подробная памятка находится также в корневом `DEPLOY.md`.

## Публикация документации

Workflow `.github/workflows/docs-pages.yml` проверяет Diplodoc-сборку в pull
request и публикует `_site` после изменения документации в ветке `main`.

Перед первым запуском откройте **Settings → Pages** репозитория и выберите
**Source: GitHub Actions**. После успешного workflow документация будет
доступна по адресу `https://nikuvolen.github.io/promocode-service/`.
