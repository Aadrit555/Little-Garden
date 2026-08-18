import json
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.db_models import CEFRLevel, ContentItem, Skill
from content.generate_reading import create_item, generate_one

router = APIRouter(prefix="/content", tags=["content"])


class GenerateRequest(BaseModel):
    skill: Skill
    level: CEFRLevel
    count: int = Field(default=1, ge=1, le=20)


class ReviewRequest(BaseModel):
    decision: str


class ListeningIngestRequest(BaseModel):
    level: CEFRLevel
    limit: int = Field(default=1, ge=1, le=20)


class SpeakingIngestRequest(BaseModel):
    level: CEFRLevel
    limit: int = Field(default=1, ge=1, le=20)
    dataset_dir: str


def _public_item(item: ContentItem) -> dict:
    questions = []
    if item.skill == Skill.reading and item.answer_key:
        try:
            questions = list(json.loads(item.answer_key).keys())
        except json.JSONDecodeError:
            raise HTTPException(500, "Approved reading item has invalid answer data")

    return {
        "id": item.id,
        "skill": item.skill.value,
        "level": item.level.value,
        "text_content": item.text_content,
        "audio_path": item.audio_path,
        "questions": questions,
        "source": item.source,
    }


def _safe_local_audio_path(audio_path: str) -> str:
    if audio_path.startswith(("http://", "https://")):
        raise HTTPException(400, "Content audio is hosted remotely; use audio_path")
    path = os.path.abspath(audio_path)
    if not os.path.isfile(path):
        raise HTTPException(404, "Content audio file not found")
    return path


@router.get("/available")
def available_content(skill: Skill, db: Session = Depends(get_db)):
    rows = (
        db.query(ContentItem.level)
        .filter(ContentItem.skill == skill, ContentItem.reviewed == "approved")
        .distinct()
        .all()
    )
    approved = db.query(ContentItem).filter(ContentItem.skill == skill, ContentItem.reviewed == "approved").count()
    pending = db.query(ContentItem).filter(ContentItem.skill == skill, ContentItem.reviewed == "pending").count()
    return {
        "skill": skill.value,
        "levels": sorted({row[0].value for row in rows}),
        "approved_count": approved,
        "pending_count": pending,
    }


@router.get("/status")
def content_status(db: Session = Depends(get_db)):
    return {
        skill.value: {
            "approved": db.query(ContentItem).filter(ContentItem.skill == skill, ContentItem.reviewed == "approved").count(),
            "pending": db.query(ContentItem).filter(ContentItem.skill == skill, ContentItem.reviewed == "pending").count(),
            "rejected": db.query(ContentItem).filter(ContentItem.skill == skill, ContentItem.reviewed == "rejected").count(),
        }
        for skill in Skill
    }


@router.get("/admin/pending")
def pending_content(db: Session = Depends(get_db)):
    rows = db.query(ContentItem).filter(ContentItem.reviewed == "pending").order_by(ContentItem.id).all()
    return [
        {
            "id": item.id,
            "skill": item.skill.value,
            "level": item.level.value,
            "text_content": item.text_content,
            "audio_path": item.audio_path,
            "answer_key": json.loads(item.answer_key) if item.answer_key else None,
            "source": item.source,
        }
        for item in rows
    ]


@router.post("/admin/generate")
def generate_content(req: GenerateRequest, db: Session = Depends(get_db)):
    if req.skill not in {Skill.reading, Skill.writing}:
        raise HTTPException(400, "Local LLM generation supports reading and writing only")

    created = []
    for _ in range(req.count):
        generated = generate_one(req.skill, req.level)
        item = create_item(req.skill, req.level, generated)
        db.add(item)
        db.flush()
        created.append(item.id)

    db.commit()
    return {"created_ids": created, "count": len(created), "status": "pending"}


@router.post("/admin/ingest-listening")
def ingest_listening(req: ListeningIngestRequest, db: Session = Depends(get_db)):
    from content.ingest import ingest_listening_from_dw

    try:
        count = ingest_listening_from_dw(db, req.level, req.limit)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Listening ingestion failed: {exc}") from exc
    return {"count": count, "status": "pending"}


@router.post("/admin/ingest-speaking")
def ingest_speaking(req: SpeakingIngestRequest, db: Session = Depends(get_db)):
    from content.ingest import ingest_speaking_from_commonvoice

    try:
        count = ingest_speaking_from_commonvoice(db, req.level, req.limit, req.dataset_dir)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Speaking ingestion failed: {exc}") from exc
    return {"count": count, "status": "pending"}


@router.post("/admin/{content_id}/review")
def review_content(content_id: int, req: ReviewRequest, db: Session = Depends(get_db)):
    decision = req.decision.strip().lower()
    if decision not in {"approved", "rejected"}:
        raise HTTPException(400, "Decision must be approved or rejected")

    item = db.query(ContentItem).filter(ContentItem.id == content_id).first()
    if not item:
        raise HTTPException(404, "Content item not found")

    item.reviewed = decision
    db.commit()
    return {"id": item.id, "reviewed": item.reviewed}


@router.get("/")
def list_content(skill: Skill, level: CEFRLevel, db: Session = Depends(get_db)):
    items = db.query(ContentItem).filter(
        ContentItem.skill == skill,
        ContentItem.level == level,
        ContentItem.reviewed == "approved",
    ).all()
    return [_public_item(item) for item in items]


@router.get("/{content_id}")
def get_content(content_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(
        ContentItem.id == content_id,
        ContentItem.reviewed == "approved",
    ).first()
    if not item:
        raise HTTPException(404, "Approved content item not found")
    return _public_item(item)


@router.get("/admin/{content_id}/audio")
def get_review_audio(content_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == content_id).first()
    if not item or not item.audio_path:
        raise HTTPException(404, "Content item has no audio")
    return FileResponse(_safe_local_audio_path(item.audio_path))


@router.get("/{content_id}/audio")
def get_local_audio(content_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(
        ContentItem.id == content_id,
        ContentItem.reviewed == "approved",
    ).first()
    if not item or not item.audio_path:
        raise HTTPException(404, "Approved content item has no audio")
    return FileResponse(_safe_local_audio_path(item.audio_path))
