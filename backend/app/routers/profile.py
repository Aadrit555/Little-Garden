from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.models.db_models import Submission, Learner, Skill

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{learner_id}")
def get_profile(learner_id: int, db: Session = Depends(get_db)):
    """
    Real profile, computed live from actual submission history.
    No fixed/default skill levels — a skill with zero real submissions
    shows as "not yet assessed", never a fabricated placeholder score.
    """
    learner = db.query(Learner).filter(Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(404, "Learner not found")

    breakdown = {}
    for skill in Skill:
        completed = (
            db.query(Submission)
            .filter(
                Submission.learner_id == learner_id,
                Submission.skill == skill,
                Submission.pipeline_status == "done",
            )
            .order_by(Submission.completed_at.desc())
            .limit(10)
            .all()
        )
        if not completed:
            breakdown[skill.value] = {"status": "not_yet_assessed", "avg_score": None, "attempts": 0}
            continue

        avg_score = sum(s.score for s in completed) / len(completed)
        latest_level = completed[0].estimated_level.value if completed[0].estimated_level else None
        breakdown[skill.value] = {
            "status": "assessed",
            "avg_score": round(avg_score, 1),
            "latest_estimated_level": latest_level,
            "attempts": len(completed),
        }

    return {
        "learner_id": learner.id,
        "display_name": learner.display_name,
        "skill_breakdown": breakdown,
    }
