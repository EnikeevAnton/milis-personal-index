import pandas as pd
import math
from config import INSALES_PRODUCTS_FILE


def get_prepared_catalog():
    print(f"[Data Processing] Чтение файла {INSALES_PRODUCTS_FILE}...")
    try:
        df = pd.read_csv(INSALES_PRODUCTS_FILE, sep='\t',
                         dtype=str, encoding='utf-16')
    except UnicodeError:
        df = pd.read_csv(INSALES_PRODUCTS_FILE, sep=';',
                         dtype=str, encoding='cp1251')

    # очистка чисел
    df['Остаток'] = pd.to_numeric(df['Остаток'].fillna(
        '0').str.replace(',', '.'), errors='coerce').fillna(0)
    df['Цена продажи'] = pd.to_numeric(df['Цена продажи'].fillna(
        '0').str.replace(',', '.'), errors='coerce').fillna(0)
    df['Старая цена'] = pd.to_numeric(df['Старая цена'].fillna(
        '0').str.replace(',', '.'), errors='coerce').fillna(0)

    # строгий фильтр: только "Выставлен"
    if 'Видимость на витрине' in df.columns:
        df = df[df['Видимость на витрине'].str.strip().str.lower()
                == 'выставлен']

    print("[Data Processing] Группировка вариантов в товары...")

    grouped = df.groupby('ID товара').agg(
        title=('Название товара или услуги', 'first'),
        url=('URL', 'first'),
        brand=('Параметр: Бренд', 'first'),
        gender=('Параметр: Пол', 'first'),
        category_lvl3=('Параметр: Тип', 'first'),
        category_lvl2=('Параметр: Тип2', 'first'),
        category_lvl1=('Параметр: Тип3', 'first'),
        season=('Параметр: Сезон', 'first'),
        price=('Цена продажи', 'min'),
        old_price=('Старая цена', 'max'),
        total_stock=('Остаток', 'sum'),
        sizes=('Свойство: Размер', lambda x: list(set(x.dropna()))),
        colors=('Свойство: Цвет', lambda x: list(set(x.dropna()))),
        barcodes=('Штрих-код', lambda x: list(set(x.dropna()))),
        images=('Изображения', lambda x: str(x.iloc[0]).split() if pd.notna(
            x.iloc[0]) and str(x.iloc[0]).strip() else [])
    ).reset_index()

    grouped['in_stock'] = grouped['total_stock'] > 0
    grouped['is_sale'] = (grouped['old_price'] >
                          grouped['price']) & (grouped['price'] > 0)
    grouped['discount'] = 0

    # расчет процента скидки
    sale_mask = grouped['is_sale']
    grouped.loc[sale_mask, 'discount'] = (
        (grouped['old_price'] - grouped['price']) / grouped['old_price'] * 100).round()

    # расчет is_new
    if 'Параметр: новинка' in df.columns:
        grouped_new = df.groupby('ID товара')['Параметр: новинка'].first()
        grouped['is_new'] = grouped['ID товара'].map(grouped_new).apply(
            lambda x: str(x).strip().lower() == 'да' if pd.notna(x) else False
        )
    else:
        grouped['is_new'] = False

    # порядок колонок
    ordered_columns = [
        'ID товара', 'title', 'url', 'brand', 'gender',
        'category_lvl3', 'category_lvl2', 'category_lvl1', 'season',
        'price', 'old_price', 'discount', 'total_stock', 'sizes',
        'colors', 'barcodes', 'images', 'in_stock', 'is_sale', 'is_new'
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

        doc['barcodes'] = [str(v) for v in doc.get(
            'barcodes', []) if pd.notna(v) and str(v).strip()]

        doc['total_views'] = 0
        doc['total_purchases'] = 0
        doc['popularity'] = 0.0
        doc['novelty'] = 14.0

        boost = 1.5 if doc['in_stock'] else 0.05
        if doc['is_sale']:
            boost *= 1.2
        if doc['is_new']:
            boost *= 1.3

        doc['final_score'] = round(
            math.log(math.e + 0.0) * (doc['novelty'] / 14.0) * boost, 4)

        documents.append(doc)

    print(
        f"[Data Processing] Подготовлено {len(documents)} уникальных товаров")
    return documents
