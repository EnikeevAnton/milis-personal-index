from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from engine.evaluation import run_evaluation
from config import EVALUATION_TEST_DAYS, EVALUATION_TOP_K, TARGET_DATE
from engine.formulas import POPULARITY_WINDOW

router = APIRouter(prefix="/api/v1/analytics", tags=["2. Analytics & Metrics"])


@router.get("/evaluate", summary="Оценка качества алгоритмов (Оффлайн A/B тестирование)")
def trigger_evaluation(
    target_date: str = Query(
        TARGET_DATE, description="Целевая дата (Верхняя граница). Формат: YYYY-MM-DD HH:MM:SS"
    ),
    filter_query: Optional[str] = Query(
        None,
        description="Оценить в конкретном сегменте (например: `brand = 'Carhartt WIP'` или `types = 'Кепки'`)"
    ),
    score_types: List[str] = Query(
        ['commercial_score', 'final_score', 'popularity'],
        description="Какие формулы хотим сравнить между собой?"
    ),
    k: int = Query(EVALUATION_TOP_K,
                   description="Глубина оценки (Топ-K товаров)"),
    test_days: int = Query(
        EVALUATION_TEST_DAYS, description="Кол-во дней для проверки (Test окно)"),
    history_days: int = Query(
        POPULARITY_WINDOW, description="Окно логов для обучения (Train окно)")
):
    """
    Инструмент для маркетологов/менеджеров.
    Позволяет мгновенно сравнить, какая формула ранжирования принесла бы больше выручки (Revenue Recall) 
    и покупок (NDCG) в заданном сегменте товаров.
    """
    try:
        report = run_evaluation(
            target_date_str=target_date,
            test_days=test_days,
            history_days=history_days,
            k=k,
            score_types=score_types,
            filter_query=filter_query
        )
        return {
            "status": "success",
            "metrics_report": report
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Evaluation Failed: {str(e)}")
