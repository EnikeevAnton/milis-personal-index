import os
import meilisearch
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# paths
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = os.path.join(BASE_DIR, "data")

# каталоги
INSALES_PRODUCTS_FILE = os.path.join(DATA_DIR, "shop_data-10.04.2026 2.csv")
MINDBOX_PRODUCTS_FILE = os.path.join(DATA_DIR, "products-mindbox.csv")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.csv")

# логи действий
ACTIONS_DIR = os.path.join(DATA_DIR, "customers-actions")
ACTIONS_FILE_TEMPLATE = os.path.join(
    ACTIONS_DIR,
    "mindbox_filtered_actions_part_{index:02d}_of_18.json"
)

# настройки времени и метрик оценки ранжирования
# Верхняя граница (настоящее время) для скоринга и логов
TARGET_DATE = "2026-04-09 23:59:59"
# Размер тестового окна для Time-Split (расчет метрик)
EVALUATION_TEST_DAYS = 7
# Глубина (Топ-K) для оценки метрик (Precision@K, NDCG@K и т.д.)
EVALUATION_TOP_K = 30

# encodings (кодировки файлов)
ENCODING_CATALOG_MAIN = "utf-16"         # Основной файл shop_data
# Таблицы Mindbox (products, categories)
ENCODING_MINDBOX_TABLES = "utf-8-sig"
ENCODING_MINDBOX_ACTIONS = "utf-8"       # JSON логи действий пользователей

# meilisearch settings
MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY', 'masterKey')

client = meilisearch.Client(
    MEILI_URL, MEILI_MASTER_KEY if MEILI_MASTER_KEY else None
)

# базовые настройки индекса
INDEX_NAME = "kixbox_catalog"

# search_ABLE
SEARCHABLE_ATTRIBUTES = [
    "title"
]

# filter_ABLE
FILTERABLE_ATTRIBUTES = [
    "id",
    "gender",
    "brand",
    "season",
    "sizes",
    "color",
    "price",
    "discount",
    "in_stock",
    "is_sale",
    "is_new",
    "types",
    "categories",
    "category_ids"
]

# sort_ABLE
SORTABLE_ATTRIBUTES = [
    "final_score",
    "commercial_score",
    "popularity",
    "novelty",
    "price",
    "discount"
]
