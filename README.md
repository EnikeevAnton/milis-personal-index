# Прототип

## Структура проекта и данные

Проект разделен на исходный код (`src/`) и директорию с данными (`data/`).

```text
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── src/
│   ├── api.py                  # FastAPI сервер (Поисковые эндпоинты)
│   ├── config.py               # Глобальные настройки и пути
│   ├── data_processing.py      # ETL: очистка и склейка каталога
│   ├── load_data.py            # Загрузка базового каталога в Meilisearch
│   ├── main.py                 # Оркестратор: запуск скоринга и патч индекса
│   ├── formulas.py             # Математика: формулы скоров
│   ├── scoring.py              # Логика расчета Popularity, Novelty, Final Score
│   └── setup_meilisearch.py    # Инициализация индекса и фильтров
└── data/
    ├── shop_data-10.04.2026 2.csv    # Основной каталог товаров
    ├── customers.csv           # База клиентов
    ├── categories.csv          # Справочник категорий
    └── customers-actions/      # Папка с логами
        ├── data\customers-actions\mindbox_filtered_actions_part_01_of_18.json
        └── ... (всего 18 файлов)
```
> **ВАЖНО: Загрузка исходных данных**
> Таблицы с сырыми данными (CSV-файлы) не включены в репозиторий. Пользователь должен самостоятельно поместить выгрузки в папку `data/` перед запуском проекта. Названия файлов и структура папок (особенно `data/customers-actions/`) должны строго соответствовать примеру выше. Если названия ваших файлов отличаются, необходимо обновить пути в файле `src/config.py`.

## Как запустить и воспроизвести результат

### 1. Требования

- **Docker** (для запуска сервера Meilisearch)
- **Python 3.9+**

### 2. Подготовка

Клонируйте репозиторий и перейдите в папку проекта:

```bash
git clone https://github.com/EnikeevAnton/milis-personal-index.git
cd milis-personal-index
```

Создайте `.env` на основе примера:

```bash
cp .env.example .env
```

### 3. Запуск Meilisearch
Поднимите контейнер:
```bash
docker compose up --build -d
```

### 4. Установка зависимостей Python

Создайте и активируйте виртуальное окружение, а затем установите необходимые библиотеки:

Для Linux/macOS:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Для Windows:

```Bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
### 5. Запуск pipeline
Главный скрипт последовательно выполнит следующие действия:
- загрузит данные из таблиц и подготовит их
- добавит данные в индекс
- рассчитает скоры

```bash
python src/main.py
```
Вы можете проверить загруженные данные и рассчитанные скоры в интерфейсе Meilisearch по адресу http://localhost:7700 (Master Key берется из .env).

### 6. Проверка работы API (Целевые сценарии)
Вместо прямых запросов к базе, подготовили FastAPI-сервер
Для запуска API выполните:

```Bash
python src/api.py
```
После запуска откройте в браузере интерактивную документацию Swagger UI: http://127.0.0.1:8000/docs.

