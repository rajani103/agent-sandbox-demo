"""A deliberately small to-do API. The agent's task in Act 1 is to refactor
storage.py from an in-memory dict to SQLite and keep the tests green."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import storage

app = FastAPI(title="todo-api")


class TodoIn(BaseModel):
    title: str
    done: bool = False


@app.get("/todos")
def list_todos():
    return storage.list_todos()


@app.post("/todos", status_code=201)
def create_todo(todo: TodoIn):
    return storage.create_todo(todo.title, todo.done)


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    todo = storage.get_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="not found")
    return todo


@app.patch("/todos/{todo_id}/done")
def mark_done(todo_id: int):
    todo = storage.mark_done(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="not found")
    return todo


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    if not storage.delete_todo(todo_id):
        raise HTTPException(status_code=404, detail="not found")
