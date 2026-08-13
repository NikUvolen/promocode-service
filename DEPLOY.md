# Production deployment

The stack publishes a single HTTP endpoint. PostgreSQL and Redis stay inside
the Docker network, so it can run next to another Django project.

1. Copy `.env.production.example` to `.env.production` and replace every
   example value. Keep `DB_*` and matching `POSTGRES_*` values identical. Use
   a long hexadecimal secret key so `$` is not interpreted by Docker Compose.
2. Set `DJANGO_ALLOWED_HOSTS` to the public domain or server IP.
3. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the complete public HTTPS origin.
4. Keep `APP_BIND=127.0.0.1` when a host Nginx proxies the application.
5. Start the stack. `--env-file` prevents Docker Compose from accidentally
   reading local development variables:

```bash
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production exec backend python manage.py createsuperuser
```

The application is then available through the configured host proxy:

- frontend: `https://promo.example.com/`
- admin: `https://promo.example.com/admin/`
- API documentation: `https://promo.example.com/api/docs/`
- healthcheck: `https://promo.example.com/health/`

For direct access without a host reverse proxy, run Compose with
`APP_BIND=0.0.0.0`, allow port `8080` in the firewall, set the server IP in
`DJANGO_ALLOWED_HOSTS`, and use `http://SERVER_IP:8080/admin/`. Disable
HTTPS-only settings until TLS is configured:

```bash
APP_BIND=0.0.0.0 docker compose --env-file .env.production up -d --build
```

Use `deploy/nginx/host-proxy.conf.example` as the server-level Nginx virtual
host. Add TLS with the server's existing certificate workflow.

Useful commands:

```bash
docker compose --env-file .env.production ps
docker compose --env-file .env.production logs -f backend worker beat
docker compose --env-file .env.production exec backend python manage.py migrate
docker compose --env-file .env.production exec backend python manage.py collectstatic --noinput
docker compose --env-file .env.production down
```

Do not use `docker compose down -v` unless the PostgreSQL and Redis volumes may
be permanently deleted.
