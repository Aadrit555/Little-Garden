import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.base import get_db
from app.models.db_models import Submission, ContentItem, Skill, Learner
from app.services.writing_grader import grade_writing

router = APIRouter(prefix="/writing", tags=["writing"])


class WritingSubmitRequest(BaseModel):
    learner_id: int
    content_item_id: int
    text: str
    strictness: str = "standard"  # lenient | standard | strict


@router.post("/submit")
def submit_writing(req: WritingSubmitRequest, db: Session = Depends(get_db)):
    if not db.query(Learner).filter(Learner.id == req.learner_id).first():
        raise HTTPException(404, "Learner not found")

    content = db.query(ContentItem).filter(
        ContentItem.id == req.content_item_id,
        ContentItem.skill == Skill.writing,
        ContentItem.reviewed == "approved"
    ).first()
    if not content:
        raise HTTPException(404, "Writing prompt not found — content must be seeded via ingestion, not assumed to exist")

    submission = Submission(
        learner_id=req.learner_id,
        content_item_id=req.content_item_id,
        skill=Skill.writing,
        submitted_text=req.text,
        pipeline_status="processing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Real, live grading call — failure here is a real failure, surfaced
    # to the learner, not papered over with a fabricated score.
    try:
        result = grade_writing(prompt_text=content.text_content, learner_text=req.text, strictness=req.strictness)
    except Exception as e:
        submission.pipeline_status = "error"
        submission.error_detail = str(e)
        db.commit()
        raise HTTPException(502, f"Grading failed: {e}")

    submission.score = result["score"]
    submission.estimated_level = result["cefr_estimate"]
    submission.feedback_json = json.dumps(result)
    submission.pipeline_status = "done"
    submission.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)

    return {
        "submission_id": submission.id,
        "score": submission.score,
        "cefr_estimate": submission.estimated_level,
        "feedback": result,
    }
