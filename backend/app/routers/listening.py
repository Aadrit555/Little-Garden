import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.base import get_db
from app.models.db_models import Submission, ContentItem, Skill, Learner
from app.services.listening_service import grade_transcription_task

router = APIRouter(prefix="/listening", tags=["listening"])


class ListeningSubmitRequest(BaseModel):
    learner_id: int
    content_item_id: int
    typed_transcript: str


@router.post("/submit")
def submit_listening(req: ListeningSubmitRequest, db: Session = Depends(get_db)):
    if not db.query(Learner).filter(Learner.id == req.learner_id).first():
        raise HTTPException(404, "Learner not found")

    content = db.query(ContentItem).filter(
        ContentItem.id == req.content_item_id,
        ContentItem.skill == Skill.listening,
        ContentItem.reviewed == "approved"
    ).first()
    if not content:
        raise HTTPException(404, "Listening clip not found")
    if not content.text_content:
        raise HTTPException(500, "Content item missing real reference transcript — cannot grade")

    if not req.typed_transcript or not req.typed_transcript.strip():
        raise HTTPException(status_code=400, detail="Cannot submit an empty transcript.")

    submission = Submission(
        learner_id=req.learner_id,
        content_item_id=req.content_item_id,
        skill=Skill.listening,
        submitted_text=req.typed_transcript,
        pipeline_status="processing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        result = grade_transcription_task(
            learner_typed_text=req.typed_transcript,
            reference_transcript=content.text_content,
        )
    except Exception as e:
        submission.pipeline_status = "error"
        submission.error_detail = str(e)
        db.commit()
        raise HTTPException(502, f"Listening grading failed: {e}")

    submission.score = result["score"]
    submission.feedback_json = json.dumps(result)
    submission.pipeline_status = "done"
    submission.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"submission_id": submission.id, "score": submission.score, "feedback": result}
