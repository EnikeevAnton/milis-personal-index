from config import INDEX_NAME
from setup_meilisearch import setup_index
from data_processing import get_prepared_catalog
from load_data import upload_documents_to_meilisearch
from scoring import calculate_scores

# дата и время, которое является верхней границей для фильтрации событий
TARGET_DATE = "2026-04-09 23:59:59"


# main функция запуска полного пайплайна: от извлечения данных из табличек, до построения построения индекса и расчета скоров
def main():
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

    # target_date_str = get_target_date()
    target_date_str = TARGET_DATE

    print(f"[*] Целевая дата (T) установлена на: {target_date_str}")

    calculate_scores(target_date_str)

    print("\n=== ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН ===")


if __name__ == "__main__":
    main()
