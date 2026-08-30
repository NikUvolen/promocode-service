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

`/health/` является readiness-проверкой: она возвращает `200` только когда
Django может обратиться и к PostgreSQL, и к Redis. При недоступности одной из
зависимостей ответ будет `503`; Docker Compose в этом случае не считает
backend готовым.

Адреса сервиса:

- frontend: `http://SERVER_IP:8080/`;
- admin: `http://SERVER_IP:8080/admin/`;
- Swagger UI: `http://SERVER_IP:8080/api/docs/`.

## Reverse proxy and HTTP

For the current test deployment the service intentionally works over HTTP.
Keep `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE`,
`DJANGO_CSRF_COOKIE_SECURE` and `JWT_COOKIE_SECURE` set to `False` in this
mode. When TLS is added, enable these settings together and use an HTTPS URL
in `DJANGO_CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL`.

Nginx overwrites `X-Forwarded-Proto` with the protocol of its own incoming
connection. Do not change this to pass through the client header: Django uses
it to determine whether a request is secure.

## PostgreSQL backups and restore verification

The `backup` container creates a PostgreSQL custom-format dump in its isolated
`backup_data` Docker volume every day at `00:15 UTC`. Dumps older than
`BACKUP_RETENTION_DAYS` are removed. Every Sunday at `00:30 UTC` the newest
dump is restored into `BACKUP_VERIFY_DB`; the script checks the restored
`django_migrations` table and removes the temporary database afterwards.

Check the most recent backup and backup verification in the logs:

```bash
docker compose -p gear-drop --env-file .env.production \
  logs --tail=100 backup
docker compose -p gear-drop --env-file .env.production \
  exec backup ls -lh /backups
```

Run a restore verification manually after an important change:

```bash
docker compose -p gear-drop --env-file .env.production \
  exec backup /bin/sh /usr/local/bin/verify-postgres-backup
```

`backup_data` is on the same VPS and therefore does not protect against losing
the server. Regularly copy the dumps to a separate storage location and test
restoration from that copy before considering the backup strategy complete.

### Emergency restoration

Restoration drops and recreates the production database before loading the
archive. First put the application into maintenance by stopping all services
that can use PostgreSQL:

```bash
docker compose -p gear-drop --env-file .env.production \
  stop web backend worker-critical worker-notifications worker-generation worker-imports worker-reports worker-maintenance beat
docker compose -p gear-drop --env-file .env.production \
  exec backup ls -lh /backups
```

Choose a `.dump` filename from the output and run the restore. The command
requires the explicit `--confirm` flag and accepts only files located in
`/backups`:

```bash
docker compose -p gear-drop --env-file .env.production \
  exec backup /bin/sh /usr/local/bin/restore-postgres \
  --confirm promocode_service-YYYYMMDDTHHMMSSZ.dump
docker compose -p gear-drop --env-file .env.production \
  up -d
curl --fail http://127.0.0.1:8080/health/
```

## Обновление

```bash
cd /opt/gear-drop
git pull --ff-only
docker compose -p gear-drop --env-file .env.production \
  up -d --build --remove-orphans
```

## Continuous delivery

Workflow `Deploy production` запускается только после успешного workflow `CI`
для push в `main`. Pull request на сервер не развёртывается. Деплой получает
проверенный SHA, обновляет checkout в `/opt/gear-drop`, пересобирает оба
контейнера и ждёт readiness endpoint `/health/` до одной минуты.

Перед первым автодеплоем создайте отдельный SSH-ключ для GitHub Actions на
доверенной машине:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/gear-drop-github-actions \
  -C github-actions-gear-drop
```

Добавьте содержимое `~/.ssh/gear-drop-github-actions.pub` в
`~/.ssh/authorized_keys` пользователя, который владеет `/opt/gear-drop` и
может выполнять `docker compose`. Закрытый ключ храните только в GitHub
Secret, не на сервере и не в репозитории.

В **Settings → Secrets and variables → Actions** добавьте repository secrets:

| Secret | Значение |
| --- | --- |
| `DEPLOY_HOST` | IP-адрес или домен VPS |
| `DEPLOY_USER` | SSH-пользователь для деплоя |
| `DEPLOY_SSH_PRIVATE_KEY` | содержимое файла `gear-drop-github-actions` |
| `DEPLOY_KNOWN_HOSTS` | проверенная строка `known_hosts` для VPS |

В repository variables добавьте:

| Variable | Значение |
| --- | --- |
| `DEPLOY_PATH` | `/opt/gear-drop` |
| `DEPLOY_PORT` | `22`, если SSH использует стандартный порт |

Для `DEPLOY_KNOWN_HOSTS` сначала получите ключ и обязательно сверяйте его
отпечаток с выводом команды на VPS:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
ssh-keyscan -t ed25519 -H SERVER_IP
```

Первая команда показывает доверенный fingerprint сервера; только совпадающую
строку из второй команды можно сохранить в Secret. Workflow не использует
`StrictHostKeyChecking=no`.

На сервере checkout должен быть чистым и находиться в ветке `main`. Если
деплой не проходит health check, workflow завершится ошибкой и приложит логи
`backend` и `web`; автоматического отката нет, потому что миграции базы данных
могут быть необратимыми.

## Диагностика

```bash
docker compose -p gear-drop --env-file .env.production ps
docker compose -p gear-drop --env-file .env.production \
  logs --tail=200 backend web worker-critical worker-notifications worker-generation worker-imports worker-reports worker-maintenance beat
```

Не выполняйте `docker compose down -v`, если данные PostgreSQL, Redis и media
нужно сохранить. Подробная памятка находится также в корневом `DEPLOY.md`.

## Публикация документации

Workflow `.github/workflows/docs-pages.yml` проверяет Diplodoc-сборку в pull
request и публикует `_site` после изменения документации в ветке `main`.

Перед первым запуском откройте **Settings → Pages** репозитория и выберите
**Source: GitHub Actions**. После успешного workflow документация будет
доступна по адресу `https://nikuvolen.github.io/promocode-service/`.
