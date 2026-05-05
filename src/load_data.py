from config import INDEX_NAME, client


def upload_documents_to_meilisearch(documents, batch_size=5000):
    """Принимает список словарей и отправляет их в индекс Meilisearch батчами"""
    index = client.index(INDEX_NAME)

    total_docs = len(documents)
    print(
        f"[Loader] Начало отправки {total_docs} документов в Meilisearch...")

    if total_docs == 0:
        print("[Loader ERR] Нет документов для отправки.")
        return

    task_uids = []
    for i in range(0, total_docs, batch_size):
        batch = documents[i: i + batch_size]
        # send
        task = index.add_documents(batch)
        task_uids.append(task.task_uid)

    # wait
    for uid in task_uids:
        client.wait_for_task(uid)

    print("[Loader] Все данные успешно загружены")
