import pandas as pd
from typing import Dict
from collections import defaultdict
from datetime import timedelta
import heapq

from config import (
    client, INDEX_NAME, TARGET_DATE, EVALUATION_TEST_DAYS, EVALUATION_TOP_K
)
from etl.log_parser import parse_events_history
from engine.metrics import precision_at_k, ndcg_at_k, map_at_k, recall_at_k, mrr_at_k
from engine.formulas import (
    POPULARITY_WINDOW,
    calculate_day_score,
    calculate_decay,
    calculate_novelty,
    calculate_boosts,
    calculate_final_score,
    score_commercial
)


def calculate_offline_metrics(predictions: list, test_stats: dict, k: int = 30, score_key: str = 'score') -> Dict[str, float]:
    """
    Рассчитывает оффлайн-метрики ранжирования на основе предсказаний.
    predictions: список словарей [{'id': str, 'score_key': float}, ...]
    test_stats: словарь вида {pid: {'views': V, 'carts': C, 'purchases': P, 'revenue': R}}
    """
    print(
        f"\n[Evaluation Engine] Оценка качества ранжирования (Топ-{k}) по метрике '{score_key}'...")

    if not predictions or not test_stats:
        print("[!] Недостаточно данных для оценки.")
        return {"Precision@K": 0.0, "NDCG@K": 0.0, "MAP@K": 0.0, "Quantity Recall@K": 0.0, "Revenue Recall@K": 0.0, "MRR@K": 0.0}

    # Быстрый поиск Топ-K через кучу (heapq) - сложность O(N log K) вместо O(N log N)
    top_k_preds = heapq.nlargest(
        k, predictions, key=lambda x: x.get(score_key, 0.0))
    recommended_ids = [item['id'] for item in top_k_preds]

    # Подготавливаем Ground Truth структуры для metrics.py
    actual_rel_set = {
        pid for pid, stats in test_stats.items()
        if stats.get('views', 0) > 0 or stats.get('carts', 0) > 0 or stats.get('purchases', 0) > 0
    }

    actual_purchases = {
        pid: stats['purchases'] for pid, stats in test_stats.items() if stats.get('purchases', 0) > 0
    }

    actual_revenue = {
        pid: stats['revenue'] for pid, stats in test_stats.items() if stats.get('revenue', 0.0) > 0.0
    }

    metrics_res = {
        f"Precision@{k}": round(precision_at_k(actual_rel_set, recommended_ids, k), 4),
        f"NDCG@{k}": round(ndcg_at_k(actual_purchases, recommended_ids, k), 4),
        f"MAP@{k}": round(map_at_k(actual_rel_set, recommended_ids, k), 4),
        f"Quantity Recall@{k}": round(recall_at_k(actual_purchases, recommended_ids, k), 4),
        f"Revenue Recall@{k}": round(recall_at_k(actual_revenue, recommended_ids, k), 4),
        f"MRR@{k}": round(mrr_at_k(actual_rel_set, recommended_ids, k), 4)
    }

    print("="*40)
    for metric_name, val in metrics_res.items():
        print(f" {metric_name.ljust(25)} | {val:.4f}")
    print("="*40)

    return metrics_res


def run_evaluation(target_date_str: str = TARGET_DATE, test_days: int = EVALUATION_TEST_DAYS, history_days: int = POPULARITY_WINDOW, k: int = EVALUATION_TOP_K, score_types: list = None, filter_query: str = None) -> Dict[str, Dict[str, float]]:
    """
    Запускает изолированный процесс time-split валидации. 
    Парсит логи, разбивает их на Train/Test, генерирует скоры и оценивает их.
    """
    if score_types is None:
        score_types = ['commercial_score', 'final_score']

    target_date = pd.to_datetime(target_date_str).replace(tzinfo=None)
    split_date = target_date - timedelta(days=test_days)
    start_date = split_date - timedelta(days=history_days)

    start_date_cmp = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    split_date_cmp = split_date.strftime('%Y-%m-%dT%H:%M:%S')
    target_date_cmp = target_date.strftime('%Y-%m-%dT%H:%M:%S')

    print(f"\n[Evaluation Engine] Настройки валидации:")
    if filter_query:
        print(f" - Фильтр Meilisearch  : '{filter_query}'")
    print(f" - Train окно (Обучение) : {start_date_cmp} -> {split_date_cmp}")
    print(f" - Test окно (Проверка)  : {split_date_cmp} -> {target_date_cmp}")

    print("\n[Evaluation Engine] Загрузка статических фичей каталога (Read-Only)...")
    search_params = {
        'limit': 100000,
        'attributesToRetrieve': ['id', 'barcodes', 'in_stock', 'is_sale', 'is_new', 'discount', 'price']
    }
    if filter_query:
        search_params['filter'] = filter_query

    response = client.index(INDEX_NAME).search("", search_params)
    documents = response.get('hits', [])

    variant_to_product = {}
    products_info = {}

    for doc in documents:
        pid = str(doc.get('id', getattr(doc, 'id', '')))
        products_info[pid] = doc
        barcodes = doc.get('barcodes', getattr(doc, 'barcodes', []))
        for code in barcodes:
            variant_to_product[str(code)] = pid

    train_stats = defaultdict(lambda: defaultdict(
        lambda: {'views': 0, 'purchases': 0, 'carts': 0}))
    test_stats = defaultdict(
        lambda: {'views': 0, 'purchases': 0, 'carts': 0, 'revenue': 0.0})
    total_purchases_train = 0

    daily_stats, _ = parse_events_history(
        variant_to_product, start_date_cmp, target_date_cmp)

    print(f"[Evaluation Engine] Разделение логов (Time-Split)...")
    split_day_cmp = split_date.strftime('%Y-%m-%d')

    for pid, days in daily_stats.items():
        for day_str, stats in days.items():
            if day_str <= split_day_cmp:
                train_stats[pid][day_str] = stats
                total_purchases_train += stats['purchases']
            else:
                test_stats[pid]['views'] += stats['views']
                test_stats[pid]['carts'] += stats['carts']
                test_stats[pid]['purchases'] += stats['purchases']
                test_stats[pid]['revenue'] += stats['revenue']

    print("[Evaluation Engine] Генерация предсказаний на базе Train...")
    train_records = []
    product_total_purchases = {pid: sum(
        d['purchases'] for d in days.values()) for pid, days in train_stats.items()}

    for pid, doc in products_info.items():
        popularity = 0.0
        total_c = 0
        for day_str, stats in train_stats.get(pid, {}).items():
            age_days = max(0, (split_date - pd.to_datetime(day_str)).days)
            popularity += calculate_day_score(
                stats['views'], stats['purchases']) * calculate_decay(age_days)
            total_c += stats['carts']

        novelty = calculate_novelty(
            product_total_purchases.get(pid, 0), total_purchases_train)

        in_stock = doc.get('in_stock', True) if isinstance(
            doc, dict) else getattr(doc, 'in_stock', True)
        is_sale = doc.get('is_sale', False) if isinstance(
            doc, dict) else getattr(doc, 'is_sale', False)
        is_new = doc.get('is_new', False) if isinstance(
            doc, dict) else getattr(doc, 'is_new', False)
        discount_val = doc.get('discount', 0.0) if isinstance(
            doc, dict) else getattr(doc, 'discount', 0.0)

        boost = calculate_boosts(in_stock, is_sale, is_new)
        discount_frac = float(discount_val or 0.0) / 100.0

        train_records.append({
            'id': pid,
            'popularity': popularity,
            'novelty': novelty,
            'final_score': calculate_final_score(popularity, novelty, boost),
            'commercial_score': score_commercial(popularity, novelty, boost, discount_frac, total_c)
        })

    print("[Evaluation Engine] Выполнение расчетов для заданных формул...")
    results = {}
    for st in score_types:
        results[st] = calculate_offline_metrics(
            train_records, test_stats, k=k, score_key=st)

    return results


if __name__ == "__main__":
    run_evaluation(
        score_types=['popularity', 'novelty',
                     'final_score', 'commercial_score'],
        # filter_query="types = 'Головные уборы' OR brand = 'Nike'"  # <-- Укажите фильтры здесь (формат meilisearch)
    )
