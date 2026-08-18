import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.base import get_db
from app.models.db_models import Learner

router = APIRouter(prefix="/learners", tags=["learners"])


class CreateLearnerRequest(BaseModel):
    display_name: str
    email: EmailStr | None = None


@router.post("/")
def create_learner(req: CreateLearnerRequest, db: Session = Depends(get_db)):
    display_name = req.display_name.strip()
    if not display_name:
        raise HTTPException(400, "Display name cannot be empty")

    if req.email:
        existing = db.query(Learner).filter(Learner.email == req.email).first()
        if existing:
            raise HTTPException(409, "Learner with this email already exists")
        email = req.email
    else:
        email = f"{uuid.uuid4()}@local.invalid"

    learner = Learner(email=email, display_name=display_name)
    db.add(learner)
    db.commit()
    db.refresh(learner)
    return {"id": learner.id, "email": learner.email, "display_name": learner.display_name}


@router.get("/{learner_id}")
def get_learner(learner_id: int, db: Session = Depends(get_db)):
    learner = db.query(Learner).filter(Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(404, "Learner not found")
    return {"id": learner.id, "email": learner.email, "display_name": learner.display_name}
