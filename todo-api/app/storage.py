"""In-memory storage. TODO (the agent's task): move this to SQLite
without changing the function signatures."""
from itertools import count

_todos: dict[int, dict] = {}
_ids = count(1)


def reset() -> None:
    global _ids
    _todos.clear()
    _ids = count(1)


def list_todos() -> list[dict]:
    return list(_todos.values())


def create_todo(title: str, done: bool = False) -> dict:
    todo_id = next(_ids)
    todo = {"id": todo_id, "title": title, "done": done}
    _todos[todo_id] = todo
    return todo


def get_todo(todo_id: int) -> dict | None:
    return _todos.get(todo_id)


def mark_done(todo_id: int) -> dict | None:
    todo = _todos.get(todo_id)
    if todo is not None:
        todo["done"] = True
    return todo


def delete_todo(todo_id: int) -> bool:
    return _todos.pop(todo_id, None) is not None
