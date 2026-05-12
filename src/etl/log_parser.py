import os
import json
from collections import defaultdict
from config import ACTIONS_FILE_TEMPLATE, ENCODING_MINDBOX_ACTIONS


def extract_ordered_products(action_json):
    """Извлекает ID купленных вариантов, их количество и итоговую цену из заказа (онлайн/офлайн)"""
    ordered_items = []
    lines = action_json.get("order", {}).get("lines", [])
    for line in lines:
        insales_id = line.get("product", {}).get("ids", {}).get("insalesId")
        if insales_id:
            quantity = line.get("quantity", 1)
            try:
                quantity = int(float(quantity))
            except (ValueError, TypeError):
                quantity = 1

            try:
                if "priceOfLine" in line and line["priceOfLine"] is not None:
                    price = float(line["priceOfLine"])
                else:
                    price = float(line.get("basePricePerItem", 0.0)) * quantity
            except (ValueError, TypeError):
                price = 0.0

            ordered_items.append((str(insales_id), quantity, price))
    return ordered_items


def parse_events_history(variant_to_product: dict, start_date_cmp: str, end_date_cmp: str):
    """
    Универсальный парсер JSON-логов для скоринга и оценки.
    Возвращает:
    - daily_stats: dict[pid][day_str] = {'views': V, 'carts': C, 'purchases': P, 'revenue': R}
    - total_purchases_global: int (общее кол-во покупок)
    """
    daily_stats = defaultdict(lambda: defaultdict(
        lambda: {'views': 0, 'purchases': 0, 'carts': 0, 'revenue': 0.0}))
    total_purchases_global = 0

    print(f"[Log Parser] Чтение логов с {start_date_cmp[:10]} по {end_date_cmp[:10]}...")
    for i in range(1, 19):
        file_path = ACTIONS_FILE_TEMPLATE.format(index=i)
        if not os.path.exists(file_path):
            continue

        print(f" - Парсинг: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding=ENCODING_MINDBOX_ACTIONS) as f:
                data = json.load(f)
                actions = data.get("customerActions", [])
                for action in actions:
                    dt_str = action.get("dateTimeUtc")
                    if not dt_str: continue

                    dt_str_clean = dt_str[:19]
                    if not (start_date_cmp <= dt_str_clean <= end_date_cmp): continue

                    day_key = dt_str[:10]
                    template_sysname = action.get("actionTemplate", {}).get("ids", {}).get("systemName")

                    if template_sysname == "ProsmotrProdukta":
                        for p in action.get("products", []):
                            pid = variant_to_product.get(str(p.get("ids", {}).get("insalesId", "")))
                            if pid: daily_stats[pid][day_key]['views'] += 1
                    elif template_sysname == "DobavlenieProduktaVSpisok":
                        for p in action.get("products", []):
                            pid = variant_to_product.get(str(p.get("ids", {}).get("insalesId", "")))
                            if pid: daily_stats[pid][day_key]['carts'] += 1
                    elif template_sysname in ["SoxranenieZakazaVOperaciiWebsiteCreateOrder", "SoxranenieZakazaVOperaciiNewOfflineCreateAuthorizedOrder"]:
                        for insales_id, quantity, price in extract_ordered_products(action):
                            pid = variant_to_product.get(insales_id)
                            if pid:
                                daily_stats[pid][day_key]['purchases'] += quantity
                                daily_stats[pid][day_key]['revenue'] += price
                                total_purchases_global += quantity
        except Exception as e:
            print(f"[!] Ошибка чтения {os.path.basename(file_path)}: {e}")

    return daily_stats, total_purchases_global
