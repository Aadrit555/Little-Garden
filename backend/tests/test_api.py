import json


def test_core_api_and_content_gate(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    from app.db.base import Base, engine, SessionLocal
    from app.main import app
    from app.models.db_models import ContentItem, Skill, CEFRLevel

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    learner = client.post("/learners/", json={"display_name": "Test"})
    assert learner.status_code == 200
    learner_id = learner.json()["id"]
    assert client.get(f"/learners/{learner_id}").status_code == 200

    db = SessionLocal()
    pending = ContentItem(
        skill=Skill.writing,
        level=CEFRLevel.A2,
        text_content="Real generated task",
        source="local-llm-generated",
        reviewed="pending",
    )
    reading = ContentItem(
        skill=Skill.reading,
        level=CEFRLevel.A2,
        text_content="Passage",
        answer_key=json.dumps({"Wo?": "Berlin"}),
        source="local-llm-generated",
        reviewed="approved",
    )
    db.add_all([pending, reading])
    db.commit()
    pending_id, reading_id = pending.id, reading.id
    db.close()

    assert client.get("/content/available?skill=writing").json()["levels"] == []
    blocked = client.post(
        "/writing/submit",
        json={"learner_id": learner_id, "content_item_id": pending_id, "text": "Hallo"},
    )
    assert blocked.status_code == 404

    approved = client.post(
        f"/content/admin/{pending_id}/review",
        json={"decision": "approved"},
    )
    assert approved.status_code == 200
    assert client.get("/content/available?skill=writing").json()["levels"] == ["A2"]

    public = client.get(f"/content/{reading_id}")
    assert public.status_code == 200
    assert public.json()["questions"] == ["Wo?"]
    assert "answer_key" not in public.json()
