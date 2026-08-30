# Нагрузочные сценарии

Нагрузочные сценарии проверяют два наиболее тяжёлых контура: генерацию
1 500 000 промокодов и импорт XLSX-файла, близкого к лимиту
`XLSX_MAX_UPLOAD_SIZE`. Это не часть production-развёртывания: команда создаёт
реальные записи и должна работать только с отдельной базой данных.

## Подготовка isolated environment

Создайте `.env.load` на основе production-шаблона. Используйте другой Compose
project, базу и порт; не подключайтесь к production PostgreSQL.

```dotenv
DB_NAME=promocode_load
POSTGRES_DB=promocode_load
APP_PORT=8081
LOAD_TEST_ALLOWED=True
```

Запустите isolated stack и примените миграции:

```bash
docker compose -p gear-drop-load --env-file .env.load up -d --build
docker compose -p gear-drop-load --env-file .env.load \
  exec backend python manage.py migrate --noinput
```

## Запуск

Генерация 1,5 млн кодов:

```bash
docker compose -p gear-drop-load --env-file .env.load \
  exec backend python manage.py run_load_scenarios \
  --scenario generation --generation-count 1500000 --confirm
```

Импорт создаёт корректный XLSX, стремясь к текущему лимиту размера, затем
импортирует его и выводит JSON с размером файла, числом строк и скоростью:

```bash
docker compose -p gear-drop-load --env-file .env.load \
  exec backend python manage.py run_load_scenarios \
  --scenario import --confirm
```

Для обоих сценариев используйте `--scenario all`. Сохраните JSON-результаты,
версии Docker-образов и характеристики VPS: без них сравнение замеров не
показательно.

После прогона удалите isolated environment вместе с тестовыми данными:

```bash
docker compose -p gear-drop-load --env-file .env.load down -v
```
