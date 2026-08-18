import os
import json
import shutil
import subprocess
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.db_models import Submission, ContentItem, Skill, Learner
from app.services.audio_utils import resolve_ffmpeg_bin
from app.services.speaking_service import (
    transcribe_learner_speech, score_pronunciation
)

router = APIRouter(prefix="/speaking", tags=["speaking"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
ALIGN_DIR = os.environ.get("ALIGN_DIR", "./alignments")


@router.post("/submit")
async def submit_speaking(
    learner_id: int = Form(...),
    content_item_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not db.query(Learner).filter(Learner.id == learner_id).first():
        raise HTTPException(404, "Learner not found")

    content = db.query(ContentItem).filter(
        ContentItem.id == content_item_id,
        ContentItem.skill == Skill.speaking,
        ContentItem.reviewed == "approved"
    ).first()
    if not content:
        raise HTTPException(404, "Speaking prompt not found")
    if not content.audio_path:
        raise HTTPException(500, "No native reference audio seeded for this prompt — cannot score pronunciation")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    raw_ext = os.path.splitext(audio_file.filename or "")[1].lower() or ".webm"
    raw_path = os.path.join(UPLOAD_DIR, f"learner_{learner_id}_{content_item_id}_{int(datetime.now(timezone.utc).timestamp())}{raw_ext}")
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    save_path = os.path.splitext(raw_path)[0] + ".wav"
    ffmpeg_bin = resolve_ffmpeg_bin()
    if not ffmpeg_bin:
        raise HTTPException(
            500,
            "ffmpeg is required to convert browser microphone audio for speaking alignment "
            "(install ffmpeg or pip install imageio-ffmpeg)",
        )
    converted = subprocess.run(
        [ffmpeg_bin, "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", save_path],
        capture_output=True,
        text=True,
    )
    if converted.returncode != 0 or not os.path.exists(save_path):
        detail = converted.stderr.strip()[-500:] if converted.stderr else "unknown ffmpeg error"
        raise HTTPException(500, f"Microphone audio conversion failed: {detail}")

    submission = Submission(
        learner_id=learner_id,
        content_item_id=content_item_id,
        skill=Skill.speaking,
        submitted_audio_path=save_path,
        pipeline_status="processing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        from app.services.listening_service import transcribe_audio
        transcript, learner_words = transcribe_learner_speech(save_path, word_timestamps=True)
        submission.raw_transcript = transcript
        
        # Get reference words using Whisper instead of MFA
        ref_transcript, ref_words = transcribe_audio(content.audio_path, word_timestamps=True)

        result = score_pronunciation(learner_words, ref_words)
    except Exception as e:
        submission.pipeline_status = "error"
        submission.error_detail = str(e)
        db.commit()
        raise HTTPException(502, f"Speaking pipeline failed: {e}")

    submission.score = result["score"]
    submission.feedback_json = json.dumps(result)
    submission.pipeline_status = "done"
    submission.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"submission_id": submission.id, "transcript": transcript, "score": submission.score, "feedback": result}
