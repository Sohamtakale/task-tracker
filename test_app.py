import pytest
from app import app


@pytest.fixture
def client(tmp_path):
    app.config["DB_PATH"] = str(tmp_path / "test.db")
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_home_page(client):
    assert b"Task Tracker" in client.get("/").data


def test_add_and_list(client):
    assert client.post("/api/tasks", json={"title": "Learn Jenkins"}).status_code == 201
    tasks = client.get("/api/tasks").get_json()
    assert len(tasks) == 1 and tasks[0]["title"] == "Learn Jenkins"


def test_empty_title_rejected(client):
    assert client.post("/api/tasks", json={"title": "  "}).status_code == 400


def test_toggle_and_delete(client):
    tid = client.post("/api/tasks", json={"title": "x"}).get_json()["id"]
    assert client.put(f"/api/tasks/{tid}/toggle").status_code == 200
    assert client.get("/api/tasks").get_json()[0]["done"] is True
    assert client.delete(f"/api/tasks/{tid}").status_code == 200
    assert client.get("/api/tasks").get_json() == []


def test_missing_task_404(client):
    assert client.delete("/api/tasks/999").status_code == 404
