# Celery и обслуживание

Задачи маршрутизируются по характеру нагрузки. В production каждая очередь
обслуживается отдельным worker.

| Очередь | Задачи |
| --- | --- |
| `critical` | Автоматический и ручной розыгрыш |
| `notifications` | Подтверждение email, восстановление пароля, письма о кодах и победах |
| `generation` | Генерация промокодов |
| `imports` | XLSX-импорт промокодов |
| `reports` | Формирование XLSX-отчётов |
| `maintenance` | Очистка файлов и аудита, восстановление зависших задач |

## Расписание

Все значения времени относятся к `Europe/Moscow`.

| Период | Задача |
| --- | --- |
| Каждый день, 00:00 | Автоматический розыгрыш |
| Каждые 5 минут | Повтор неотправленных писем победителям |
| Каждые 15 минут | Перевод зависших фоновых операций в ошибку |
| Каждый день, 03:30 | Очистка файлов импорта |
| Каждый день, 03:35 | Очистка файлов отчетов |
| Каждый день, 03:45 | Очистка журнала аудита |

## Запуск

В Docker Compose используются сервисы:

```bash
docker compose -p gear-drop --env-file .env.production \
  up -d worker-critical worker-notifications worker-generation worker-imports worker-reports worker-maintenance beat
```

Логи:

```bash
docker compose -p gear-drop --env-file .env.production \
  logs -f worker-critical worker-notifications worker-generation worker-imports worker-reports worker-maintenance beat
```

Если задача остается в статусе `В очереди`, проверьте, что запущен worker
нужной очереди. Наличие только Redis и Beat не означает, что задача будет
выполнена.
