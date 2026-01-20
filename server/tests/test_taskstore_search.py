from app.domain.tasks import TaskStore

def test_search_tasks_returns_matches():
    store = TaskStore()
    user = "u1"
    store.create_task(user, "اجتماع الفريق", None)
    store.create_task(user, "اجتماع العميل", None)
    store.create_task(user, "دراسة NLP", None)

    res = store.search_tasks(user, "اجتماع")
    assert len(res) == 2
    assert all("اجتماع" in t.title for t in res)
