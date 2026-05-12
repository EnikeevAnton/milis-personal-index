import math

# --- Настройки скоринга ---

# коэф. действий для popularity
W_VIEWS = 0.3
W_PURCHASES = 0.7

# константа затухания (дни)
HALF_LIFE = 30

# окно от целевой даты <T> (дни)
POPULARITY_WINDOW = 30

# базовые бизнес-бусты
BOOST_IN_STOCK = 1.5
BOOST_OUT_OF_STOCK = 0.05
BOOST_SALE = 1.2
BOOST_NEW_ARRIVAL = 1

# коэф. нормализации novelty при расчете final_score
NOVELTY_NORMALIZER = 14.0

# используются для commercial_score
CART_WEIGHT = 0.5
DISCOUNT_WEIGHT = 0.5


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
    return math.log1p(popularity) * (novelty / NOVELTY_NORMALIZER) * boost


def score_commercial(popularity: float, novelty: float, boost: float, discount: float, carts: int = 0) -> float:
    """Коммерческий: Учет корзины и скидок."""
    cart_factor = math.log1p(carts * CART_WEIGHT) 
    discount_boost = 1.0 + (discount * DISCOUNT_WEIGHT)
    return (math.log1p(popularity) + cart_factor) * (novelty / NOVELTY_NORMALIZER) * boost * discount_boost
