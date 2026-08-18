"""
Real SQLAlchemy models. No mock objects, no in-memory fake data.
Every learner, submission, and score is a real row, computed live.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey, DateTime, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.db.base import Base


class Skill(str, enum.Enum):
    listening = "listening"
    speaking = "speaking"
    reading = "reading"
    writing = "writing"


class CEFRLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Learner(Base):
    __tablename__ = "learners"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submissions = relationship("Submission", back_populates="learner")


class ContentItem(Base):
    """
    Real content pulled from real corpora (Section 4 of proposal):
    listening clips, reading passages, writing prompts.
    NOTHING here is written inline in application code — this table
    is populated by the ingestion script (see content/ingest.py).
    """
    __tablename__ = "content_items"
    id = Column(Integer, primary_key=True)
    skill = Column(Enum(Skill), nullable=False)
    level = Column(Enum(CEFRLevel), nullable=False)
    # text passage (reading/writing prompt) OR transcript of audio (listening)
    text_content = Column(Text, nullable=True)
    # path/URL to real audio file (listening clips, native speaker reference for speaking)
    audio_path = Column(String, nullable=True)
    # for reading/listening: real answer key, stored as JSON string
    answer_key = Column(Text, nullable=True)
    source = Column(String, nullable=False)  # e.g. "Deutsche Welle", "Falko corpus"
    reviewed = Column(String, default="pending")  # pending|approved|rejected — human review gate before real learner exposure


class Submission(Base):
    """
    One real learner attempt at one content item. Score/feedback fields
    are NULL until the real pipeline (ASR / alignment / LLM grading)
    actually computes them — never pre-filled.
    """
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False)
    content_item_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    skill = Column(Enum(Skill), nullable=False)

    # raw learner input
    submitted_text = Column(Text, nullable=True)       # writing / reading answer
    submitted_audio_path = Column(String, nullable=True)  # speaking recording

    # computed by real pipeline — set only after real processing completes
    raw_transcript = Column(Text, nullable=True)        # real ASR output
    score = Column(Float, nullable=True)                 # real computed score, 0-100
    estimated_level = Column(Enum(CEFRLevel), nullable=True)
    feedback_json = Column(Text, nullable=True)          # structured real feedback
    pipeline_status = Column(String, default="pending")   # pending|processing|done|error
    error_detail = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    learner = relationship("Learner", back_populates="submissions")
