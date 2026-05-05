from config import (
    FILTERABLE_ATTRIBUTES,
    SEARCHABLE_ATTRIBUTES,
    SORTABLE_ATTRIBUTES,
    client
)


def setup_index(index_name, recreate=False):
    print(f"[Setup] Настройка индекса '{index_name}'...")

    if recreate:
        print(f"[Setup] Удаление старого индекса '{index_name}'...")
        try:
            task = client.delete_index(index_name)
            client.wait_for_task(task.task_uid)
        except Exception:
            pass

    # create index
    try:
        client.create_index(index_name, {'primaryKey': 'id'})
    except Exception:
        pass

    index = client.index(index_name)

    settings = {
        'filterableAttributes': FILTERABLE_ATTRIBUTES,
        'searchableAttributes': SEARCHABLE_ATTRIBUTES,
        'sortableAttributes': SORTABLE_ATTRIBUTES
    }

    print("[Setup] Отправка настроек в Meilisearch...")
    task = index.update_settings(settings)

    client.wait_for_task(task.task_uid)
    print("[Setup] Настройки успешно применены")

    return index
