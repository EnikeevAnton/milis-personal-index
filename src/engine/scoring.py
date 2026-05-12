import pandas as pd
from config import client, INDEX_NAME, TARGET_DATE
from etl.log_parser import parse_events_history
from etl.load_data import upload_documents_to_meilisearch
from engine.formulas import (
    POPULARITY_WINDOW,
    calculate_day_score,
    calculate_decay,
    calculate_novelty,
    calculate_boosts,
    calculate_final_score,
    score_commercial
)


def calculate_scores(target_date_str=None, history_days=None):
    if not target_date_str:
        target_date_str = TARGET_DATE
    if history_days is None:
        history_days = POPULARITY_WINDOW

    target_date = pd.to_datetime(target_date_str).replace(tzinfo=None)

    start_date = target_date - pd.Timedelta(days=history_days)
    print(
        f"[Scoring] Расчет окна: {start_date.strftime('%Y-%m-%d')} ---> {target_date.strftime('%Y-%m-%d')}")

    start_date_cmp = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    target_date_cmp = target_date.strftime('%Y-%m-%dT%H:%M:%S')

    print("[Scoring] Сборка словаря штрих-кодов из Meilisearch...")
    response = client.index(INDEX_NAME).get_documents(
        {'limit': 100000, 'fields': ['id', 'barcodes', 'in_stock', 'is_sale', 'is_new', 'discount']})

    variant_to_product = {}
    products_info = {}

    for doc in response.results:
        pid = str(doc.id)
        products_info[pid] = doc
        barcodes = getattr(doc, 'barcodes', doc.get(
            'barcodes', []) if isinstance(doc, dict) else [])
        for code in barcodes:
            variant_to_product[str(code)] = pid

    daily_stats, total_purchases_global = parse_events_history(
        variant_to_product, start_date_cmp, target_date_cmp
    )

    print("[Scoring] Математический расчет...")
    update_payload = []

    product_total_purchases = {pid: sum(
        d['purchases'] for d in days.values()) for pid, days in daily_stats.items()}

    for pid, doc in products_info.items():
        days_data = daily_stats.get(pid, {})

        # переменные для агрегации
        popularity = 0.0
        total_v = 0
        total_p = 0
        total_c = 0

        for day_str, stats in days_data.items():
            day_dt = pd.to_datetime(day_str)
            age_days = max(0, (target_date - day_dt).days)

            # Собираем сырые логи для аналитики
            total_v += stats['views']
            total_p += stats['purchases']
            total_c += stats['carts']

            # используем формулы (которые в отедеьном файлике)
            day_score = calculate_day_score(stats['views'], stats['purchases'])
            decay = calculate_decay(age_days)
            popularity += day_score * decay

        purchases = product_total_purchases.get(pid, 0)
        novelty = calculate_novelty(purchases, total_purchases_global)

        in_stock = getattr(doc, 'in_stock', doc.get(
            'in_stock', True) if isinstance(doc, dict) else True)
        is_sale = getattr(doc, 'is_sale', doc.get(
            'is_sale', False) if isinstance(doc, dict) else False)
        is_new = getattr(doc, 'is_new', doc.get('is_new', False)
                         if isinstance(doc, dict) else False)

        # Приводим скидку (0-100) к долям (0.0-1.0) для формулы
        discount_val = getattr(doc, 'discount', doc.get(
            'discount', 0.0) if isinstance(doc, dict) else 0.0)
        try:
            discount_frac = float(discount_val) / 100.0
        except (ValueError, TypeError):
            discount_frac = 0.0

        boost = calculate_boosts(in_stock, is_sale, is_new)
        final_score = calculate_final_score(popularity, novelty, boost)
        commercial_score = score_commercial(
            popularity, novelty, boost, discount_frac, total_c)

        update_payload.append({
            'id': pid,
            'popularity': round(popularity, 4),
            'novelty': round(novelty, 4),
            'final_score': round(final_score, 4),
            'commercial_score': round(commercial_score, 4),
        })

    upload_documents_to_meilisearch(
        update_payload, batch_size=2000, update=True)

    print("[Scoring] Движок успешно обновлен")
    return update_payload


if __name__ == "__main__":
    calculate_scores()
