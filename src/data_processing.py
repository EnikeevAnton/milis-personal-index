import os
import ast
import pandas as pd
from config import (
    INSALES_PRODUCTS_FILE, MINDBOX_PRODUCTS_FILE, CATEGORIES_FILE,
    ENCODING_CATALOG_MAIN, ENCODING_MINDBOX_TABLES
)
from formulas import calculate_boosts, calculate_final_score


def normalize_id(value) -> str:
    """Очищает ID от концевых пробелов и пустых значений."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def get_barcode_categories_mapping() -> dict[str, dict[str, str]]:
    """
    Загружает справочник категорий и Mindbox-товары, выстраивая полный
    словарь связи: штрихкод -> {id_категории: название_категории} 
    с автоматической раскруткой всей родительской иерархии.
    """
    print(
        f"[Data Processing] Загрузка справочника категорий {os.path.basename(CATEGORIES_FILE)}...")
    df_cat = pd.read_csv(CATEGORIES_FILE, sep=";",
                         dtype=str, encoding=ENCODING_MINDBOX_TABLES)

    cat_id_to_name = {}
    cat_id_to_parent = {}

    for _, row in df_cat.iterrows():
        cat_id = normalize_id(row.get("CategoryIdsInsalesId"))
        cat_name = str(row.get("CategoryName", "")).strip()

        parent_id = normalize_id(row.get("CategoryParentCategoryIdsInsalesId"))
        parent_name = str(row.get("CategoryParentCategoryName", "")).strip()

        if cat_id and cat_name:
            cat_id_to_name[cat_id] = cat_name
            if parent_id:
                cat_id_to_parent[cat_id] = parent_id
                if parent_name and parent_id not in cat_id_to_name:
                    cat_id_to_name[parent_id] = parent_name

    print(
        f"[Data Processing] Загрузка связи штрихкодов {os.path.basename(MINDBOX_PRODUCTS_FILE)}...")
    df_mb = pd.read_csv(MINDBOX_PRODUCTS_FILE, sep=";",
                        dtype=str, encoding=ENCODING_MINDBOX_TABLES)

    barcode_to_categories = {}

    for _, row in df_mb.iterrows():
        mb_insales_id = normalize_id(row.get("ProductIdsInsalesId"))
        mb_cat_id = normalize_id(row.get("ProductCategoriesIdsInsalesId"))

        if mb_insales_id and mb_cat_id and mb_cat_id in cat_id_to_name:
            if mb_insales_id not in barcode_to_categories:
                barcode_to_categories[mb_insales_id] = {}

            curr_cat_id = mb_cat_id
            seen = set()
            while curr_cat_id and curr_cat_id not in seen:
                seen.add(curr_cat_id)
                if curr_cat_id in cat_id_to_name:
                    barcode_to_categories[mb_insales_id][curr_cat_id] = cat_id_to_name[curr_cat_id]
                curr_cat_id = cat_id_to_parent.get(curr_cat_id)

    return barcode_to_categories


def get_available_sizes(stock_series) -> list:
    """Агрегирует доступные размеры из поля warehouse_stocks_kixbox"""
    available_sizes = set()
    for stock_str in stock_series.dropna():
        if not isinstance(stock_str, str) or not stock_str.strip():
            continue
        try:
            # парсим строку вида "{'M':{'106':'2'}, 'S':{'106':'0'}}"
            stock_dict = ast.literal_eval(stock_str)
            if isinstance(stock_dict, dict):
                for size, warehouses in stock_dict.items():
                    if isinstance(warehouses, dict):
                        # проверяем, есть ли хотя бы на одном складе количество > 0
                        for qty in warehouses.values():
                            try:
                                if float(qty) > 0:
                                    available_sizes.add(str(size).strip())
                                    break
                            except (ValueError, TypeError):
                                pass
        except (ValueError, SyntaxError):
            pass
    return sorted(list(available_sizes))


def get_prepared_catalog():
    # получаем готовый маппинг категорий из отдельного метода
    barcode_to_categories = get_barcode_categories_mapping()

    print(f"[Data Processing] Чтение файла {INSALES_PRODUCTS_FILE}...")
    df = pd.read_csv(INSALES_PRODUCTS_FILE, sep='\t',
                     dtype=str, encoding=ENCODING_CATALOG_MAIN)

    # Очистка числовых данных
    df['Остаток'] = pd.to_numeric(
        df['Остаток'].fillna('0').str.replace(',', '.'), errors='coerce'
    ).fillna(0)
    df['Цена продажи'] = pd.to_numeric(
        df['Цена продажи'].fillna('0').str.replace(',', '.'), errors='coerce'
    ).fillna(0)
    df['Старая цена'] = pd.to_numeric(
        df['Старая цена'].fillna('0').str.replace(',', '.'), errors='coerce'
    ).fillna(0)

    # Строгий фильтр: оставляем только "Выставлен"
    if 'Видимость на витрине' in df.columns:
        df = df[df['Видимость на витрине'].str.strip().str.lower()
                == 'выставлен']

    print("[Data Processing] Группировка вариантов в товары...")

    agg_dict = {
        'title': ('Название товара или услуги', 'first'),
        'url': ('URL', 'first'),
        'brand': ('Параметр: Бренд', 'first'),
        'gender': ('Параметр: Пол', 'first'),
        'type1': ('Параметр: Тип', 'first'),
        'type2': ('Параметр: Тип2', 'first'),
        'type3': ('Параметр: Тип3', 'first'),
        'season': ('Параметр: Сезон', 'first'),
        'price': ('Цена продажи', 'min'),
        'old_price': ('Старая цена', 'max'),
        'total_stock': ('Остаток', 'sum'),
        'colors': ('Свойство: Цвет', lambda x: list(set(x.dropna()))),
        'barcodes': ('Штрих-код', lambda x: list(set(x.dropna()))),
        'variant_ids': ('ID варианта', lambda x: list(set(x.dropna()))),
        'images': ('Изображения', lambda x: str(x.iloc[0]).split()[:2] if pd.notna(
            x.iloc[0]) and str(x.iloc[0]).strip() else [])
    }

    stock_col = 'Дополнительное поле: warehouse_stocks_kixbox'
    if stock_col in df.columns:
        agg_dict['sizes'] = (stock_col, get_available_sizes)
    else:
        agg_dict['sizes'] = ('Свойство: Размер',
                             lambda x: list(set(x.dropna())))

    grouped = df.groupby('ID товара').agg(**agg_dict).reset_index()

    grouped['in_stock'] = grouped['total_stock'] > 0
    grouped['is_sale'] = (grouped['old_price'] >
                          grouped['price']) & (grouped['price'] > 0)
    grouped['discount'] = 0

    # Расчет процента скидки
    sale_mask = grouped['is_sale']
    grouped.loc[sale_mask, 'discount'] = (
        (grouped['old_price'] - grouped['price']) / grouped['old_price'] * 100
    ).round()

    # Расчет флага новинки
    if 'Параметр: новинка' in df.columns:
        grouped_new = df.groupby('ID товара')['Параметр: новинка'].first()
        grouped['is_new'] = grouped['ID товара'].map(grouped_new).apply(
            lambda x: str(x).strip().lower() == 'да' if pd.notna(x) else False
        )
    else:
        grouped['is_new'] = False

    # Фиксация итогового порядка колонок
    ordered_columns = [
        'ID товара', 'title', 'url', 'brand', 'gender',
        'type1', 'type2', 'type3', 'season',
        'price', 'old_price', 'discount', 'total_stock', 'sizes',
        'colors', 'barcodes', 'variant_ids', 'images', 'in_stock', 'is_sale', 'is_new'
    ]
    grouped = grouped[ordered_columns]

    documents = []

    for _, row in grouped.iterrows():
        doc = row.to_dict()
        doc['id'] = doc.pop('ID товара')

        for k, v in list(doc.items()):
            if isinstance(v, list):
                continue
            if pd.isna(v):
                doc[k] = None

        # Сборка типов в единый упорядоченный список
        doc['types'] = []
        for t_field in ['type1', 'type2', 'type3']:
            t_val = doc.pop(t_field, None)
            if t_val is not None and str(t_val).strip():
                doc['types'].append(str(t_val).strip())

        doc['barcodes'] = [str(v) for v in doc.get(
            'barcodes', []) if pd.notna(v) and str(v).strip()]
        doc['variant_ids'] = [str(v) for v in doc.get(
            'variant_ids', []) if pd.notna(v) and str(v).strip()]

        # --- Сопоставление и извлечение полной ветки категорий ---
        unique_cats = {}
        for bc in doc['barcodes']:
            norm_bc = normalize_id(bc)
            if norm_bc in barcode_to_categories:
                unique_cats.update(barcode_to_categories[norm_bc])

        # Гарантированное сохранение индексов: каждой id_категории строго соответствует её название
        doc['category_ids'] = list(unique_cats.keys())
        doc['categories'] = list(unique_cats.values())

        doc['total_views'] = 0
        doc['total_purchases'] = 0
        doc['popularity'] = 0.0
        doc['novelty'] = 14.0

        boost = calculate_boosts(
            doc['in_stock'], doc['is_sale'], doc['is_new'])
        doc['final_score'] = round(calculate_final_score(
            doc['popularity'], doc['novelty'], boost), 4)

        documents.append(doc)

    print(
        f"[Data Processing] Подготовлено {len(documents)} уникальных товаров")
    return documents
