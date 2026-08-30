# Нагрузочные сценарии

Нагрузочные сценарии проверяют два наиболее тяжёлых контура: генерацию
1 500 000 промокодов и импорт XLSX-файла, близкого к лимиту
`XLSX_MAX_UPLOAD_SIZE`. Это не часть production-развёртывания: команда создаёт
реальные записи и должна работать только с отдельной базой данных.

## Подготовка isolated environment

Создайте локальный файл окружения по шаблону:

```bash
cp .env.load.example .env.load
```

Шаблон уже задаёт отдельные Compose-volumes, базу `promocode_load`, порт
`127.0.0.1:8081` и `LOAD_TEST_ALLOWED=True`. Не меняйте в нём `DB_HOST` на
production-хост и не запускайте команды без `-p gear-drop-load`.

Соберите образ, запустите только PostgreSQL и Redis, затем примените миграции:

```bash
docker compose -p gear-drop-load --env-file .env.load build backend
docker compose -p gear-drop-load --env-file .env.load up -d db redis
docker compose -p gear-drop-load --env-file .env.load \
  run --rm --no-deps backend python manage.py migrate --noinput
```

## Запуск

Генерация 1,5 млн кодов:

```bash
docker compose -p gear-drop-load --env-file .env.load \
  run --rm --no-deps backend python manage.py run_load_scenarios \
  --scenario generation --generation-count 1500000 --confirm
```

Импорт создаёт корректный XLSX, стремясь к текущему лимиту размера, затем
импортирует его и выводит JSON с размером файла, числом строк и скоростью:

```bash
docker compose -p gear-drop-load --env-file .env.load \
  run --rm --no-deps backend python manage.py run_load_scenarios \
  --scenario import --confirm
```

Для обоих сценариев используйте `--scenario all`. Сохраните JSON-результаты,
версии Docker-образов и характеристики VPS: без них сравнение замеров не
показательно.

После прогона удалите isolated environment вместе с тестовыми данными:

```bash
docker compose -p gear-drop-load --env-file .env.load down -v
```
