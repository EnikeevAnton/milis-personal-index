import os
import meilisearch
from dotenv import load_dotenv

load_dotenv()

# paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# каталог продуктов
INSALES_PRODUCTS_FILE = os.path.join(DATA_DIR, "shop_data-10.04.2026 2.csv")

# логи действий
ACTIONS_DIR = os.path.join(DATA_DIR, "customers-actions")
ACTIONS_FILE_TEMPLATE = os.path.join(
    ACTIONS_DIR,
    "mindbox_filtered_actions_part_{index:02d}_of_18.json"
)

# meilisearch settings
MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY', 'masterKey')

client = meilisearch.Client(
    MEILI_URL, MEILI_MASTER_KEY if MEILI_MASTER_KEY else None
)

# index conf
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
    "category_lvl1",
    "category_lvl2",
    "category_lvl3"
]

# sort_ABLE
SORTABLE_ATTRIBUTES = [
    "final_score",
    "popularity",
    "novelty",
    "price",
    "discount"
]
