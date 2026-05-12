import os
import sys
from pathlib import Path


src_path = Path(__file__).resolve().parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# fmt: off
# isort: off
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from api.routers.admin import router as admin_router  # noqa: E402
from api.routers.analytics import router as analytics_router  # noqa: E402
from api.routers.search import router as search_router  # noqa: E402
# isort: on
# fmt: on

app = FastAPI(
    title="KixBox Search API",
    description="""
    Универсальный API поисково-рекомендательной системы.
    Создан для удобного тестирования и управления выдачей без написания кода.
    """,
    version="2.0.0"
)

# Регистрация роутеров в приложении
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(admin_router)


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    # Смена рабочей директории на корень проекта для загрузки .env и путей
    project_root = src_path.parent
    os.chdir(project_root)

    print("="*50)
    print("Запуск KixBox API Engine...")
    print(f"Документация Swagger: http://127.0.0.1:8000/docs")
    print("="*50)

    uvicorn.run("api.server:app", host="127.0.0.1", port=8000,
                reload=True, log_level="warning", app_dir=str(src_path))
