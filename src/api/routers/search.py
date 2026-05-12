from fastapi import APIRouter, Query, HTTPException
import meilisearch
from typing import Optional
from config import client, INDEX_NAME
from api.schemas import SortDirection, SortField

router = APIRouter(prefix="/api/v1/search",
                   tags=["1. Search & Recommendations"])


@router.get("/recommend", summary="Универсальная выдача товаров (Витрина)")
def get_recommendations(
    q: str = Query(
        "", description="Поисковый запрос (например: 'куртка', 'кепка')"),
    limit: int = Query(
        20, ge=1, le=500, description="Количество выводимых товаров"),
    sort_by: SortField = Query(
        SortField.commercial_score, description="Главный критерий сортировки"),
    sort_dir: SortDirection = Query(
        SortDirection.desc, description="Направление сортировки"),
    filter_query: Optional[str] = Query(
        None,
        description="Умный фильтр (например: `types = 'Футболка' AND is_sale = true` или `brand = 'Nike'`)"
    )
):
    """
    Единый мощный endpoint для фронтенда магазина. 
    Вы можете вбить любые фильтры прямо в строку `filter_query` и протестировать выдачу.
    """
    # Извлекаем реальные названия полей из Enum (обрезая русские пояснения до скобок)
    actual_sort_field = sort_by.name
    actual_sort_dir = "asc" if "asc" in sort_dir.name else "desc"

    sort_list = [f"{actual_sort_field}:{actual_sort_dir}"]

    # Автоматическое разрешение ничьих (Tie-breaker)
    if actual_sort_field != "final_score":
        sort_list.append("final_score:desc")

    params = {
        "limit": limit,
        "sort": sort_list,
    }

    if filter_query:
        params["filter"] = filter_query

    try:
        result = client.index(INDEX_NAME).search(q, params)

        # Обработка случая: индекс существует, но абсолютно пустой (нет товаров)
        if result.get("estimatedTotalHits", len(result.get("hits", []))) == 0:
            stats = client.index(INDEX_NAME).get_stats()
            if stats.number_of_documents == 0:
                raise HTTPException(
                    status_code=404, detail="Индекс пуст (нет данных). Запустите полную переиндексацию (POST /api/v1/admin/pipeline/trigger).")

        return {
            "meta": {
                "total_hits": result.get("estimatedTotalHits", len(result.get("hits", []))),
                "applied_sort": sort_list
            },
            "data": result.get("hits", [])
        }

    except meilisearch.errors.MeilisearchApiError as e:
        # Обработка случая: индекс еще не настроен и не создан в Meilisearch
        if e.code == "index_not_found":
            raise HTTPException(
                status_code=404, detail="Индекс не настроен. Запустите полную переиндексацию (POST /api/v1/admin/pipeline/trigger).")
        raise HTTPException(
            status_code=400, detail=f"Search Engine API Error: {e.message}")
    except HTTPException:
        raise  # Прокидываем наши 404 ошибки дальше
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
