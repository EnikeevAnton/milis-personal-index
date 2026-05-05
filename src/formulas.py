import math

# --- Настройки скоринга ---
W_VIEWS = 0.3
W_PURCHASES = 0.7

HALF_LIFE = 30
POPULARITY_WINDOW = 30

BOOST_IN_STOCK = 1.5
BOOST_OUT_OF_STOCK = 0.05
BOOST_SALE = 1.2
BOOST_NEW_ARRIVAL = 1
NOVELTY_NORMALIZER = 14.0


def calculate_day_score(views: int, purchases: int) -> float:
    """Оценивает ценность действий за один день"""
    return (views * W_VIEWS) + (purchases * W_PURCHASES)


def calculate_decay(age_days: int) -> float:
    """Считает экспоненциальное затухание в зависимости от возраста события"""
    decay_lambda = math.log(2) / HALF_LIFE
    return math.exp(-decay_lambda * age_days)


def calculate_novelty(item_purchases: int, total_global_purchases: int) -> float:
    """Считает редкость товара"""
    return -math.log2((item_purchases + 1) / (total_global_purchases + 1))


def calculate_boosts(in_stock: bool, is_sale: bool, is_new: bool) -> float:
    """Собирает бизнес-множители товара"""
    boost = BOOST_IN_STOCK if in_stock else BOOST_OUT_OF_STOCK
    if is_sale:
        boost *= BOOST_SALE
    if is_new:
        boost *= BOOST_NEW_ARRIVAL
    return boost


def calculate_final_score(popularity: float, novelty: float, boost: float) -> float:
    """Итоговая формула ранжирования"""
    return math.log(1 + popularity) * (novelty / NOVELTY_NORMALIZER) * boost
