from config import INDEX_NAME, client


def upload_documents_to_meilisearch(documents, batch_size=5000, update=False):
    """Принимает список словарей и отправляет их в индекс Meilisearch батчами"""
    index = client.index(INDEX_NAME)

    total_docs = len(documents)
    action_name = "обновления" if update else "отправки"
    print(
        f"[Loader] Начало {action_name} {total_docs} документов в Meilisearch...")

    if total_docs == 0:
        print("[Loader ERR] Нет документов для обработки.")
        return

    task_uids = []
    for i in range(0, total_docs, batch_size):
        batch = documents[i: i + batch_size]
        if update:
            task = index.update_documents(batch)
        else:
            task = index.add_documents(batch)
        task_uids.append(task.task_uid)

    # wait
    for uid in task_uids:
        client.wait_for_task(uid)

    print("[Loader] Все данные успешно обработаны")
