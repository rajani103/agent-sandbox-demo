import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_storage():
    storage.reset()
    yield
    storage.reset()


def test_create_and_list():
    r = client.post("/todos", json={"title": "write slides"})
    assert r.status_code == 201
    assert r.json() == {"id": 1, "title": "write slides", "done": False}
    assert len(client.get("/todos").json()) == 1


def test_get_missing_returns_404():
    assert client.get("/todos/99").status_code == 404


def test_mark_done():
    client.post("/todos", json={"title": "rehearse demo"})
    r = client.patch("/todos/1/done")
    assert r.status_code == 200
    assert r.json()["done"] is True


def test_delete():
    client.post("/todos", json={"title": "book cab"})
    assert client.delete("/todos/1").status_code == 204
    assert client.get("/todos/1").status_code == 404
