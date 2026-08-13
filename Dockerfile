FROM python:3.14-slim AS backend-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /srv/app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --active --no-install-project

FROM python:3.14-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends --yes libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /opt/venv /opt/venv
WORKDIR /srv/app
COPY app ./app
WORKDIR /srv/app/app

RUN python manage.py collectstatic --noinput

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

FROM node:24-alpine AS frontend-build

WORKDIR /srv/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:1.29-alpine AS web
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /srv/frontend/dist /usr/share/nginx/html
