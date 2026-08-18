import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.base import get_db
from app.models.db_models import Submission, ContentItem, Skill, Learner
from app.services.reading_grader import score_reading_session

router = APIRouter(prefix="/reading", tags=["reading"])


class ReadingAnswer(BaseModel):
    question: str
    learner_answer: str


class ReadingSubmitRequest(BaseModel):
    learner_id: int
    content_item_id: int
    answers: list[ReadingAnswer]


@router.post("/submit")
def submit_reading(req: ReadingSubmitRequest, db: Session = Depends(get_db)):
    if not db.query(Learner).filter(Learner.id == req.learner_id).first():
        raise HTTPException(404, "Learner not found")

    content = db.query(ContentItem).filter(
        ContentItem.id == req.content_item_id,
        ContentItem.skill == Skill.reading,
        ContentItem.reviewed == "approved"
    ).first()
    if not content:
        raise HTTPException(404, "Reading passage not found")
    if not content.answer_key:
        raise HTTPException(500, "Content item has no real answer key seeded — cannot grade")

    try:
        real_answer_key = json.loads(content.answer_key)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, "Reading content has invalid answer data") from exc

    submitted_questions = [a.question for a in req.answers]
    expected_questions = list(real_answer_key.keys())
    if set(submitted_questions) != set(expected_questions) or len(submitted_questions) != len(expected_questions):
        raise HTTPException(400, "All reading questions must be answered exactly once")

    graded_input = []
    for a in req.answers:
        expected = real_answer_key.get(a.question)
        if expected is None:
            raise HTTPException(400, f"No matching answer key for question: {a.question}")
        graded_input.append({"question": a.question, "expected": expected, "learner": a.learner_answer})

    submission = Submission(
        learner_id=req.learner_id,
        content_item_id=req.content_item_id,
        skill=Skill.reading,
        submitted_text=json.dumps([a.dict() for a in req.answers]),
        pipeline_status="processing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        result = score_reading_session(graded_input)
    except Exception as e:
        submission.pipeline_status = "error"
        submission.error_detail = str(e)
        db.commit()
        raise HTTPException(502, f"Reading grading failed: {e}")

    submission.score = result["score"]
    submission.feedback_json = json.dumps(result)
    submission.pipeline_status = "done"
    submission.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"submission_id": submission.id, "score": submission.score, "feedback": result}
