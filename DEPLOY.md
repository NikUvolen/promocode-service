# Production deployment

Gear Drop runs as an independent Docker Compose project and publishes port
`8080` directly. The other application keeps port `80`; the projects do not
share a Docker network. PostgreSQL and Redis are available only to Gear Drop
containers.

1. Copy `.env.production.example` to `.env.production` and replace every
   example value. Keep `DB_*` and matching `POSTGRES_*` values identical. Use
   a long hexadecimal secret key so `$` is not interpreted by Docker Compose.
2. Replace `SERVER_IP` in `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` with the server IP.
3. Keep `APP_BIND=0.0.0.0` and `APP_PORT=8080` for direct access.
4. Allow `8080/tcp` in the server firewall.
5. Start the stack with a fixed Compose project name:

```bash
docker compose -p gear-drop --env-file .env.production up -d --build --remove-orphans
docker compose -p gear-drop --env-file .env.production exec backend python manage.py createsuperuser
```

The application is available directly on port `8080`:

- frontend: `http://SERVER_IP:8080/`
- admin: `http://SERVER_IP:8080/admin/`
- API documentation: `http://SERVER_IP:8080/api/docs/`
- healthcheck: `http://SERVER_IP:8080/health/`

Useful commands:

```bash
docker compose -p gear-drop --env-file .env.production ps
docker compose -p gear-drop --env-file .env.production logs -f backend worker-critical worker-notifications worker-bulk beat
docker compose -p gear-drop --env-file .env.production exec backend python manage.py migrate
docker compose -p gear-drop --env-file .env.production down
```

Do not use `docker compose down -v` unless the PostgreSQL and Redis volumes may
be permanently deleted.
