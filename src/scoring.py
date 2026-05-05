import pandas as pd
import os
import json
from collections import defaultdict
from datetime import datetime
from config import ACTIONS_FILE_TEMPLATE, client, INDEX_NAME

from formulas import (
    POPULARITY_WINDOW,
    calculate_day_score,
    calculate_decay,
    calculate_novelty,
    calculate_boosts,
    calculate_final_score
)


def extract_ordered_products(action_json):
    """Извлекает ID купленных вариантов из заказа (онлайн/офлайн)"""
    ordered_ids = []
    lines = action_json.get("order", {}).get("lines", [])
    for line in lines:
        insales_id = line.get("product", {}).get("ids", {}).get("insalesId")
        if insales_id:
            ordered_ids.append(insales_id)
    return ordered_ids


def calculate_scores(target_date_str=None):
    if not target_date_str:
        target_date = datetime.now()
    else:
        target_date = pd.to_datetime(target_date_str).replace(tzinfo=None)

    start_date = target_date - pd.Timedelta(days=POPULARITY_WINDOW)
    print(
        f"[Scoring] Расчет окна: {start_date.strftime('%Y-%m-%d')} ---> {target_date.strftime('%Y-%m-%d')}")

    start_date_cmp = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    target_date_cmp = target_date.strftime('%Y-%m-%dT%H:%M:%S')

    print("[Scoring] Сборка словаря штрих-кодов из Meilisearch...")
    response = client.index(INDEX_NAME).get_documents(
        {'limit': 100000, 'fields': ['id', 'barcodes', 'in_stock', 'is_sale', 'is_new']})

    variant_to_product = {}
    products_info = {}

    for doc in response.results:
        pid = str(doc.id)
        products_info[pid] = doc
        barcodes = getattr(doc, 'barcodes', doc.get(
            'barcodes', []) if isinstance(doc, dict) else [])
        for code in barcodes:
            variant_to_product[str(code)] = pid

    daily_stats = defaultdict(lambda: defaultdict(
        lambda: {'views': 0, 'purchases': 0}))
    total_purchases_global = 0

    print(f"[Scoring] Чтение логов...")
    for i in range(1, 19):
        file_path = ACTIONS_FILE_TEMPLATE.format(index=i)
        if not os.path.exists(file_path):
            continue

        print(f" - Парсинг: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                actions = data.get("customerActions", [])
                for action in actions:
                    dt_str = action.get("dateTimeUtc")
                    if not dt_str:
                        continue

                    dt_str_clean = dt_str[:19]
                    if not (start_date_cmp <= dt_str_clean <= target_date_cmp):
                        continue

                    day_key = dt_str[:10]
                    template_sysname = action.get("actionTemplate", {}).get(
                        "ids", {}).get("systemName")

                    if template_sysname == "ProsmotrProdukta":
                        for p in action.get("products", []):
                            insales_id = p.get("ids", {}).get("insalesId")
                            if insales_id:
                                pid = variant_to_product.get(str(insales_id))
                                if pid:
                                    daily_stats[pid][day_key]['views'] += 1

                    elif template_sysname in ["SoxranenieZakazaVOperaciiWebsiteCreateOrder", "SoxranenieZakazaVOperaciiNewOfflineCreateAuthorizedOrder"]:
                        ordered_ids = extract_ordered_products(action)
                        for insales_id in ordered_ids:
                            pid = variant_to_product.get(str(insales_id))
                            if pid:
                                daily_stats[pid][day_key]['purchases'] += 1
                                total_purchases_global += 1
        except Exception as e:
            print(f"[!] Ошибка чтения {os.path.basename(file_path)}: {e}")

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

        for day_str, stats in days_data.items():
            day_dt = pd.to_datetime(day_str)
            age_days = max(0, (target_date - day_dt).days)

            # Собираем сырые логи для аналитики
            total_v += stats['views']
            total_p += stats['purchases']

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

        boost = calculate_boosts(in_stock, is_sale, is_new)
        final_score = calculate_final_score(popularity, novelty, boost)

        update_payload.append({
            'id': pid,
            'popularity': round(popularity, 4),
            'novelty': round(novelty, 4),
            'final_score': round(final_score, 4),
            # число покупок и просмтров для аналитики
            'total_views': total_v,
            'total_purchases': total_p
        })

    print(f"[Scoring] Отправка обновлений ({len(update_payload)} док-тов)...")
    batch_size = 2000
    for i in range(0, len(update_payload), batch_size):
        batch = update_payload[i:i + batch_size]
        client.index(INDEX_NAME).update_documents(batch)

    print("[Scoring] Движок успешно обновлен")
    return update_payload


if __name__ == "__main__":
    calculate_scores()
