import threading
from fastapi import APIRouter, BackgroundTasks, Query, HTTPException
from engine.scoring import calculate_scores
from main import main as run_full_pipeline
from config import TARGET_DATE
from engine.formulas import POPULARITY_WINDOW

router = APIRouter(prefix="/api/v1/admin", tags=["3. System Management"])

# Глобальное состояние для блокировки одновременного запуска тяжелых задач
task_lock = threading.Lock()
task_state = {
    "is_running": False,
    "task_name": None
}


@router.post("/scoring/recalculate", summary="Принудительный пересчет скоров")
def trigger_rescoring(
    background_tasks: BackgroundTasks,
    target_date: str = Query(
        TARGET_DATE, description="Целевая дата. Формат: YYYY-MM-DD HH:MM:SS"),
    history_days: int = Query(
        POPULARITY_WINDOW, description="Кол-во дней для расчета (Окно логов)")
):
    """
    Запускает скрипт `scoring.py` для пересчета Popularity, Novelty и Commercial Score 
    на основе логов. Выполняется в фоне (Background Task), чтобы не блокировать интерфейс API.
    """
    with task_lock:
        if task_state["is_running"]:
            raise HTTPException(
                status_code=409,
                detail=f"Уже выполняется задача: {task_state['task_name']}. Пожалуйста, дождитесь её завершения."
            )
        task_state["is_running"] = True
        task_state["task_name"] = "Пересчет скоров"

    def run_scoring_task():
        try:
            calculate_scores(target_date, history_days)
        except Exception as e:
            print(f"[Admin] Ошибка пересчета скоров: {e}")
        finally:
            with task_lock:
                task_state["is_running"] = False
                task_state["task_name"] = None

    background_tasks.add_task(run_scoring_task)
    return {
        "status": "accepted",
        "message": f"Задача пересчета скоров до {target_date} (окно: {history_days} дн.) запущена."
    }


@router.post("/pipeline/trigger", summary="Запуск полного пайплайна (ETL -> Индекс -> Скоринг)")
def trigger_pipeline(
    background_tasks: BackgroundTasks,
    target_date: str = Query(
        TARGET_DATE, description="Целевая дата. Формат: YYYY-MM-DD HH:MM:SS"),
    history_days: int = Query(
        POPULARITY_WINDOW, description="Кол-во дней для расчета (Окно логов)")
):
    """
    Запускает полный цикл обновления данных (эквивалентно запуску `python src/main.py`).
    Включает в себя: сборку каталога, пересоздание индекса в Meilisearch, парсинг логов и расчет баллов.
    Выполняется в фоне.
    """
    with task_lock:
        if task_state["is_running"]:
            raise HTTPException(
                status_code=409,
                detail=f"Уже выполняется задача: {task_state['task_name']}. Пожалуйста, дождитесь её завершения."
            )
        task_state["is_running"] = True
        task_state["task_name"] = "Полный пайплайн (ETL + Индексация)"

    def run_pipeline_task():
        try:
            run_full_pipeline(target_date, history_days)
        except Exception as e:
            print(f"[Admin] Ошибка выполнения пайплайна: {e}")
        finally:
            with task_lock:
                task_state["is_running"] = False
                task_state["task_name"] = None

    background_tasks.add_task(run_pipeline_task)
    return {
        "status": "accepted",
        "message": f"Полный пайплайн до {target_date} запущен в фоне. Отслеживайте процесс в консоли."
    }
