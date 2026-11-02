import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app

DEMO_PAYLOAD = {
    "messages": [
        {"user": "alice", "text": "We're blocked on the staging cert."},
        {"user": "sam", "text": "Sam will renew it today."},
    ],
    "title": "Demo daily",
}


@pytest.fixture(autouse=True)
def deterministic_settings(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    monkeypatch.setattr(settings, "SLACK_BOT_TOKEN", "")
    monkeypatch.setattr(settings, "SLACK_CHANNEL_ID", "")


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def create_report(client):
    response = client.post("/api/v1/demo/report", json=DEMO_PAYLOAD)
    assert response.status_code == 200, response.text
    return response.json()


def test_ai_status_reports_mock_provider(client):
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock"
    assert data["requested_provider"] == "mock"
    assert data["live"] is False


def test_demo_report_persists_items(client):
    data = create_report(client)
    assert data["mode"] == "rules"
    assert data["report_id"]
    categories = [item["category"] for item in data["items"]]
    assert "blocker" in categories
    assert "action_item" in categories

    action = next(item for item in data["items"] if item["category"] == "action_item")
    assert action["assignee"] == "sam"
    assert 0 < action["confidence"] <= 1


def test_done_state_survives_reload(client):
    data = create_report(client)
    item = next(item for item in data["items"] if item["category"] == "action_item")

    patched = client.patch(
        f"/api/v1/reports/{data['report_id']}/items/{item['id']}",
        json={"done": True},
    )
    assert patched.status_code == 200
    assert patched.json()["item"]["done"] is True

    reloaded = client.get(f"/api/v1/reports/{data['report_id']}").json()
    stored = next(entry for entry in reloaded["items"] if entry["id"] == item["id"])
    assert stored["done"] is True


def test_item_can_be_edited_and_reordered(client):
    data = create_report(client)
    item = data["items"][0]

    patched = client.patch(
        f"/api/v1/reports/{data['report_id']}/items/{item['id']}",
        json={"description": "Edited text", "position": 99},
    )
    assert patched.status_code == 200
    assert patched.json()["item"]["description"] == "Edited text"

    reloaded = client.get(f"/api/v1/reports/{data['report_id']}").json()
    assert reloaded["items"][-1]["id"] == item["id"]


def test_empty_description_is_rejected(client):
    data = create_report(client)
    item = data["items"][0]
    response = client.patch(
        f"/api/v1/reports/{data['report_id']}/items/{item['id']}",
        json={"description": "   "},
    )
    assert response.status_code == 400


def test_wrong_correction_is_recorded(client):
    data = create_report(client)
    item = data["items"][0]

    response = client.post(
        f"/api/v1/reports/{data['report_id']}/items/{item['id']}/correction",
        json={"verdict": "wrong", "note": "not a real blocker"},
    )
    assert response.status_code == 200
    assert response.json()["item_status"] == "flagged"

    listing = client.get(f"/api/v1/reports/{data['report_id']}/corrections").json()
    assert listing["corrections"][0]["verdict"] == "wrong"
    assert listing["corrections"][0]["note"] == "not a real blocker"


def test_invalid_verdict_is_rejected(client):
    data = create_report(client)
    item = data["items"][0]
    response = client.post(
        f"/api/v1/reports/{data['report_id']}/items/{item['id']}/correction",
        json={"verdict": "maybe"},
    )
    assert response.status_code == 400


def test_item_can_be_deleted(client):
    data = create_report(client)
    item = data["items"][0]

    response = client.delete(f"/api/v1/reports/{data['report_id']}/items/{item['id']}")
    assert response.status_code == 200

    reloaded = client.get(f"/api/v1/reports/{data['report_id']}").json()
    assert all(entry["id"] != item["id"] for entry in reloaded["items"])


def test_exports_render_in_all_formats(client):
    data = create_report(client)
    for export_format in ("markdown", "slack", "email"):
        response = client.get(
            f"/api/v1/reports/{data['report_id']}/export",
            params={"format": export_format},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["format"] == export_format
        assert "Demo daily" in body["content"]


def test_unknown_export_format_is_rejected(client):
    data = create_report(client)
    response = client.get(
        f"/api/v1/reports/{data['report_id']}/export",
        params={"format": "pdf"},
    )
    assert response.status_code == 400


def test_slack_post_without_token_explains_the_fix(client):
    data = create_report(client)
    response = client.post(
        "/api/v1/slack/post",
        json={"report_id": data["report_id"], "channel": "C123"},
    )
    assert response.status_code == 400
    assert "Slack token" in response.json()["detail"]


def test_demo_requires_messages(client):
    response = client.post("/api/v1/demo/report", json={"messages": []})
    assert response.status_code == 422
