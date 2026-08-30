# API и авторизация

Базовый префикс API: `/api/v1/`. Актуальная OpenAPI-схема доступна по
`/api/schema/`, интерактивный Swagger UI — по `/api/docs/`.

## Авторизация и профиль

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| POST | `/api/v1/auth/register/` | Регистрация пользователя |
| POST | `/api/v1/auth/verify-email/` | Подтверждение email |
| POST | `/api/v1/auth/resend-verification/` | Повторное письмо подтверждения |
| POST | `/api/v1/auth/login/` | Создание сессии |
| GET | `/api/v1/auth/session/` | Проверка сессии и получение CSRF cookie |
| POST | `/api/v1/auth/refresh/` | Обновление JWT-сессии |
| POST | `/api/v1/auth/logout/` | Выход и blacklist refresh-токена |
| POST | `/api/v1/auth/password-reset/` | Запрос восстановления пароля |
| POST | `/api/v1/auth/password-reset-confirm/` | Установка нового пароля по токену |
| POST | `/api/v1/auth/change-password/` | Смена пароля по старому паролю |
| GET, PATCH | `/api/v1/auth/profile/` | Просмотр и изменение профиля |
| GET, PATCH | `/api/v1/auth/notification-settings/` | Настройки писем о промокодах |

## Промокоды и результаты

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| GET | `/api/v1/promo-codes/` | Пагинированный список кодов пользователя |
| GET | `/api/v1/promo-codes/registration-status/` | Готовность профиля и состояние блокировки |
| POST | `/api/v1/promo-codes/register/` | Регистрация кода |
| GET | `/api/v1/draws/` | Публичный список завершенных розыгрышей |

## JWT и CSRF

Access и refresh JWT хранятся в HttpOnly cookies и недоступны JavaScript.
Изменяющие состояние запросы с cookie-аутентификацией должны передавать CSRF
token. Клиент сначала вызывает `GET /api/v1/auth/session/`, затем отправляет
значение cookie `csrftoken` в заголовке `X-CSRFToken`.

После смены или восстановления пароля refresh-токены пользователя блокируются.
Logout также заносит текущий refresh-токен в blacklist и очищает auth cookies.

## Ограничения запросов

Частоты регистрации, входа, email-операций и refresh настраиваются переменными
`AUTH_REGISTER_RATE`, `AUTH_LOGIN_RATE`, `AUTH_EMAIL_RATE` и
`AUTH_REFRESH_RATE`. `POST /api/v1/promo-codes/register/` дополнительно
ограничен по пользователю переменной `PROMO_CODE_REGISTER_RATE` (по умолчанию
`20/minute`), включая валидные запросы. Его ответ `429` содержит
`retry_after`.

Отдельный сервис ограничивает три неудачных попытки ввода кода за минуту и
блокирует следующие попытки на пять минут. В этом случае `429` также содержит
`reason` и `blocked_until`.

## Публичные результаты

`GET /api/v1/draws/` кешируется на `PUBLIC_DRAWS_CACHE_TIMEOUT` секунд (по
умолчанию пять минут), чтобы не выполнять одинаковую сериализацию победителей
на каждом открытии лендинга. Кэш сбрасывается после фиксации изменений
розыгрыша, победителя или отображаемого профиля победителя.
