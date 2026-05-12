import sys
from pathlib import Path


src_path = Path(__file__).resolve().parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# fmt: off
# isort: off
from config import INDEX_NAME, TARGET_DATE  # noqa: E402
from etl.setup_meilisearch import setup_index  # noqa: E402
from etl.data_processing import get_prepared_catalog  # noqa: E402
from etl.load_data import upload_documents_to_meilisearch  # noqa: E402
from engine.scoring import calculate_scores  # noqa: E402
# isort: on
# fmt: on

# функция запуска полного пайплайна: от извлечения данных из табличек,
#                                    до построения индекса и расчета скоров


def main(target_date_str=None, history_days=None):
    print("=== ЗАПУСК ПАЙПЛАЙНА MEILISEARCH & SCORING ===")

    print("\n--- ЭТАП 1: Настройка движка ---")
    setup_index(INDEX_NAME, recreate=True)

    print("\n--- ЭТАП 2: ETL Каталога ---")
    documents = get_prepared_catalog()

    if not documents:
        print("[!] Ошибка: Нет документов для загрузки. Пайплайн остановлен.")
        return

    print("\n--- ЭТАП 3: Индексация базового каталога ---")
    upload_documents_to_meilisearch(documents)

    print("\n--- ЭТАП 4: Расчет Скоринга (Scoring Engine) ---")

    target_date_to_use = target_date_str if target_date_str else TARGET_DATE

    print(f"[*] Целевая дата (T) установлена на: {target_date_to_use}")
    if history_days is not None:
        print(f"[*] Окно истории (дни) установлено на: {history_days}")

    calculate_scores(target_date_to_use, history_days)

    print("\n=== ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН ===")


if __name__ == "__main__":
    main()
