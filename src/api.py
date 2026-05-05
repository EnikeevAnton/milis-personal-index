from fastapi import FastAPI, Query
from typing import Optional
from enum import Enum
from config import client, INDEX_NAME
import uvicorn
import os

app = FastAPI(
    title="KixBox Search API",
    description="""
    API для получения отранжированных товаров из Meilisearch (Прототип).

    В системе реализован алгоритм автоматического разрешения ничьих. Если первичный критерий сортировки 
    (размер скидки, балл новизны или популярность) совпадает у нескольких товаров, система автоматически 
    применяет **final_score:desc** в качестве вторичного фильтра. 
    
    Это гарантирует, что внутри групп с одинаковыми параметрами (например, при одинаковой скидке -50%) 
    пользователь всегда увидит сначала наиболее коммерчески привлекательные и актуальные товары.
    """,
    version="1.0.2"
)

# enums


class GenderEnum(str, Enum):
    male = "Муж"
    female = "Жен"
    unisex = "Унисекс"


class SortDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class SortField(str, Enum):
    final_score = "final_score"
    popularity = "popularity"
    novelty = "novelty"
    discount = "discount"
    price = "price"

# вспомогательная функция


def build_search_params(
    limit: int,
    sort_by: str,
    sort_dir: str,
    in_stock: Optional[bool] = None,
    is_sale: Optional[bool] = None,
    is_new: Optional[bool] = None,
    gender: Optional[str] = None,
    category_lvl1: Optional[str] = None,
    category_lvl2: Optional[str] = None,
    category_lvl3: Optional[str] = None
):
    # формируем очередь сортировки
    sort_query = f"{sort_by}:{sort_dir}"
    sort_list = [sort_query]

    # ничьи - добавляем final_score вторым приоритетом
    if sort_by != "final_score":
        sort_list.append("final_score:desc")

    params = {
        "limit": limit,
        "sort": sort_list
    }

    # сборка фильтров
    filters = []
    if in_stock is not None:
        filters.append(f"in_stock = {str(in_stock).lower()}")
    if is_sale is not None:
        filters.append(f"is_sale = {str(is_sale).lower()}")
    if is_new is not None:
        filters.append(f"is_new = {str(is_new).lower()}")  # <-- ДОБАВЛЕНО
    if gender:
        filters.append(f"gender = '{gender}'")

    # типы товаров
    if category_lvl1:
        filters.append(f"category_lvl1 = '{category_lvl1}'")
    if category_lvl2:
        filters.append(f"category_lvl2 = '{category_lvl2}'")
    if category_lvl3:
        filters.append(f"category_lvl3 = '{category_lvl3}'")

    if filters:
        params["filter"] = [" AND ".join(filters)]

    return params


# для страницы новинки
@app.get("/api/pages/new", tags=["Target Pages"], summary="Выдача для страницы 'Новинки'")
def get_new_arrivals(
    limit: int = Query(10, ge=1, le=100, description="Количество товаров"),
    sort: SortField = Query(SortField.final_score,
                            description="Поле сортировки"),
    order: SortDirection = Query(
        SortDirection.desc, description="Направление"),
    in_stock: Optional[bool] = Query(True, description="Только в наличии"),
    is_new: Optional[bool] = Query(True, description="Только новые коллекции")
):
    """
    Возвращает товары из новых поступлений (is_new = true), 
    отсортированные по их коммерческой привлекательности (final_score).
    """
    params = build_search_params(
        limit=limit, sort_by=sort.value, sort_dir=order.value,
        in_stock=in_stock, is_new=is_new  # Передаем новый параметр
    )
    result = client.index(INDEX_NAME).search("", params)
    return {"query_params": params, "hits": result.get("hits", [])}


# для страницы распродажа
@app.get("/api/pages/sale", tags=["Target Pages"], summary="Выдача для страницы 'Распродажа'")
def get_sale_items(
    limit: int = Query(10, ge=1, description="Количество товаров"),
    sort: SortField = Query(SortField.discount, description="Поле сортировки"),
    order: SortDirection = Query(
        SortDirection.desc, description="Направление"),
    in_stock: Optional[bool] = Query(True, description="Только в наличии"),
    is_sale: Optional[bool] = Query(True, description="Фильтр скидки")
):
    """
    Возвращает товары с установленным флагом распродажи (is_sale = true).
    """
    params = build_search_params(limit=limit, sort_by=sort.value,
                                 sort_dir=order.value, in_stock=in_stock, is_sale=is_sale)
    result = client.index(INDEX_NAME).search("", params)
    return {"query_params": params, "hits": result.get("hits", [])}


# страница """""мужское "
@app.get("/api/pages/mens", tags=["Target Pages"], summary="Выдача для категории 'Мужское'")
def get_mens_items(
    limit: int = Query(10, ge=1, description="Количество товаров"),
    sort: SortField = Query(SortField.final_score,
                            description="Поле сортировки"),
    order: SortDirection = Query(
        SortDirection.desc, description="Направление"),
    in_stock: Optional[bool] = Query(True, description="Только в наличии"),
    gender: Optional[GenderEnum] = Query(
        GenderEnum.male, description="Фильтр по полу")
):
    """
    Фильтрует товары по гендерному признаку. По умолчанию: Мужской пол.
    """
    gender_val = gender.value if gender else None
    params = build_search_params(limit=limit, sort_by=sort.value,
                                 sort_dir=order.value, in_stock=in_stock, gender=gender_val)
    result = client.index(INDEX_NAME).search("", params)
    return {"query_params": params, "hits": result.get("hits", [])}


# страница куртки
@app.get("/api/pages/jackets", tags=["Target Pages"], summary="Выдача для категории 'Куртки'")
def get_jackets(
    limit: int = Query(10, ge=1, description="Количество товаров"),
    sort: SortField = Query(SortField.final_score,
                            description="Поле сортировки"),
    order: SortDirection = Query(
        SortDirection.desc, description="Направление"),
    in_stock: Optional[bool] = Query(True, description="Только в наличии"),
    category_lvl2: Optional[str] = Query(
        "Куртка", description="Средний уровень категории")
):
    """
    Фильтрует товары по точному совпадению названия категории на 2-м уровне иерархии.
    """
    params = build_search_params(limit=limit, sort_by=sort.value,
                                 sort_dir=order.value, in_stock=in_stock,
                                 category_lvl2=category_lvl2)
    result = client.index(INDEX_NAME).search("", params)
    return {"query_params": params, "hits": result.get("hits", [])}


# универсальная ручка для тестов и прочего
@app.get("/api/search/custom", tags=["Debug & Testing"], summary="Песочница для любых комбинаций")
def custom_search(
    q: str = Query("", description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=500),
    sort: SortField = Query(SortField.final_score),
    order: SortDirection = Query(SortDirection.desc),
    in_stock: Optional[bool] = Query(
        None, description="null = игнорировать наличие"),
    is_sale: Optional[bool] = Query(None),
    is_new: Optional[bool] = Query(
        None, description="Фильтр по новым коллекциям"),
    gender: Optional[GenderEnum] = Query(None),
    category_lvl1: Optional[str] = Query(
        None, description="Верхний уровень (напр. Одежда)"),
    category_lvl2: Optional[str] = Query(
        None, description="Средний уровень (напр. Верхняя одежда)"),
    category_lvl3: Optional[str] = Query(
        None, description="Нижний уровень (напр. Ветровки)")
):
    """
    Свободный поиск без предустановленных фильтров для проверки работы всех параметров.
    """
    gender_val = gender.value if gender else None
    params = build_search_params(
        limit=limit,
        sort_by=sort.value,
        sort_dir=order.value,
        in_stock=in_stock,
        is_sale=is_sale,
        is_new=is_new,
        gender=gender_val,
        category_lvl1=category_lvl1,
        category_lvl2=category_lvl2,
        category_lvl3=category_lvl3
    )

    result = client.index(INDEX_NAME).search(q, params)
    return {"query_params": params, "hits": result.get("hits", [])}


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    print("="*50)
    print("Запуск API...")
    print(f"Документация Swagger: http://127.0.0.1:8000/docs")
    print("="*50)

    uvicorn.run("api:app", host="127.0.0.1", port=8000,
                reload=True, log_level="warning")
