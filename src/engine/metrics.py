import math
import heapq


def precision_at_k(actual_ids: set, recommended_ids: list, k: int) -> float:
    """Доля релевантных товаров среди K рекомендованных."""
    if not recommended_ids or k <= 0:
        return 0.0
    top_k = recommended_ids[:k]
    hits = sum(1 for item in top_k if item in actual_ids)
    return float(hits) / k


def ndcg_at_k(actual_gains: dict, recommended_ids: list, k: int) -> float:
    """
    Normalized Discounted Cumulative Gain. 
    Учитывает как релевантность (вес действия из actual_gains), так и позицию в выдаче.
    """
    if not recommended_ids or not actual_gains or k <= 0:
        return 0.0

    top_k = recommended_ids[:k]
    dcg = 0.0
    for i, item in enumerate(top_k):
        gain = actual_gains.get(item, 0.0)
        if gain > 0:
            dcg += gain / math.log2(i + 2)

    ideal_gains = heapq.nlargest(k, actual_gains.values())
    idcg = sum(gain / math.log2(i + 2) for i, gain in enumerate(ideal_gains))

    return float(dcg / idcg) if idcg > 0 else 0.0


def map_at_k(actual_ids: set, recommended_ids: list, k: int) -> float:
    """Mean Average Precision для бинарной релевантности."""
    if not recommended_ids or not actual_ids or k <= 0:
        return 0.0

    top_k = recommended_ids[:k]
    hits = 0
    sum_precisions = 0.0
    for i, item in enumerate(top_k):
        if item in actual_ids:
            hits += 1
            sum_precisions += hits / (i + 1)

    return float(sum_precisions / min(k, len(actual_ids)))


def recall_at_k(actual_weights: dict, recommended_ids: list, k: int) -> float:
    """Универсальный Recall. Может использоваться для Quantity Recall или Revenue Recall."""
    if not recommended_ids or not actual_weights or k <= 0:
        return 0.0

    top_k = recommended_ids[:k]
    retrieved_weight = sum(actual_weights.get(item, 0.0) for item in top_k)
    total_weight = sum(actual_weights.values())

    return float(retrieved_weight / total_weight) if total_weight > 0 else 0.0


def mrr_at_k(actual_ids: set, recommended_ids: list, k: int) -> float:
    """Mean Reciprocal Rank — вес позиции первого найденного релевантного товара."""
    if not recommended_ids or not actual_ids or k <= 0:
        return 0.0

    for i, item in enumerate(recommended_ids[:k]):
        if item in actual_ids:
            return 1.0 / (i + 1)
    return 0.0
