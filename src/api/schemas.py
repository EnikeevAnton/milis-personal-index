from enum import Enum


class SortDirection(str, Enum):
    asc = "По возрастанию (asc)"
    desc = "По убыванию (desc)"


class SortField(str, Enum):
    final_score = "final_score (Общий балл)"
    commercial_score = "commercial_score (Коммерческий балл)"
    popularity = "popularity (Популярность)"
    novelty = "novelty (Новизна)"
    discount = "discount (Скидка %)"
    price = "price (Цена)"
