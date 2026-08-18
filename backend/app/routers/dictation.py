"""
Real local speech-to-text endpoint. Uses the same real Whisper pipeline
as listening/speaking (app/services/listening_service.transcribe_audio),
no cloud call. Used by the Writing dictation feature (speak instead of
type, still graded as real written German) and can be reused anywhere
audio-to-text is needed.

Browser speech recognition is not used. Dictation goes through local Whisper so audio stays on the machine.
"""
import os
import shutil
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.listening_service import transcribe_audio

router = APIRouter(prefix="/dictate", tags=["dictation"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")


@router.post("/")
async def dictate(audio_file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f"dictation_{uuid.uuid4().hex}.webm")
    with open(save_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    try:
        transcript = transcribe_audio(save_path)
    except Exception as e:
        raise HTTPException(502, f"Dictation failed: {e}")

    return {"transcript": transcript}
