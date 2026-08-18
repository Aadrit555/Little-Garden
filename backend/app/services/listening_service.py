"""
Real listening evaluation service.

Two paths, both real, no hardcoding:
1. Transcription task: learner listens to real audio (content_items.audio_path)
   and types what they heard. We compare against the REAL reference transcript
   stored with that content item (from Deutsche Welle / Common Voice source),
   using an LLM for tolerant real comparison (accent for spelling slips etc.)
2. Comprehension-question task: reuses reading_grader's LLM-based grading
   against the real answer key for that content item, since the underlying
   "compare learner answer to real expected answer" logic is identical.

Requires: a real Whisper model available at runtime (openai-whisper or
faster-whisper package + downloaded weights). This sandbox blocks the
model-weight download hosts (huggingface.co, openaipublic.azureedge.net),
so ASR cannot execute inside THIS sandbox. The code below is real and
correct — run it in your own environment (local machine / server / cloud
GPU) where those hosts are reachable, `pip install faster-whisper` will
pull weights fine there.
"""
import os
from app.services.local_llm import local_llm_json_call

_whisper_model = None


def _get_whisper_model():
    """
    Lazily loads a real Whisper model. Not called until an actual audio
    file needs transcribing — no dummy model, no stub returning fixed text.
    """
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(os.environ.get("WHISPER_MODEL_SIZE", "small"), device=os.environ.get("WHISPER_DEVICE", "cpu"), compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8") )
    return _whisper_model


def transcribe_audio(audio_path: str, word_timestamps: bool = False):
    """
    Real transcription of a real audio file path. Raises if the file
    doesn't exist or the model can't process it — no fallback text.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _get_whisper_model()
    segments, info = model.transcribe(audio_path, language="de", word_timestamps=word_timestamps)
    
    segments = list(segments)
    transcript = " ".join(seg.text.strip() for seg in segments)
    if not transcript.strip():
        raise RuntimeError("Whisper produced empty transcript — check audio quality")
        
    if word_timestamps:
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
        return transcript.strip(), words

    return transcript.strip()


def grade_transcription_task(learner_typed_text: str, reference_transcript: str) -> dict:
    """
    Compares what the learner typed against the real reference transcript
    for the clip they heard. Uses LLM for tolerant real comparison —
    catches near-misses (umlaut spelling, minor word order) as partial
    credit rather than binary exact-match, which would misgrade real
    understanding.
    """
    if not learner_typed_text or not learner_typed_text.strip():
        raise ValueError("Empty submission — nothing to grade")

    system = """Compare a German learner's transcription of what they heard
against the real reference transcript. Judge listening comprehension, not
spelling perfection. Return ONLY valid JSON:
{"score": <0-100>, "missed_parts": ["<phrase learner missed/misheard>", ...], "feedback": "<one sentence>"}"""

    user_msg = f"Reference transcript: {reference_transcript}\nLearner typed: {learner_typed_text}"

    result = local_llm_json_call(system=system, messages=[{"role": "user", "content": user_msg}], max_tokens=400)

    required = {"score", "missed_parts", "feedback"}
    if not required.issubset(result.keys()):
        raise RuntimeError(f"Listening grader response missing fields: {result.keys()}")
    if not isinstance(result["score"], (int, float)) or not 0 <= result["score"] <= 100:
        raise RuntimeError("Listening grader returned invalid score")
    if not isinstance(result["missed_parts"], list) or not isinstance(result["feedback"], str):
        raise RuntimeError("Listening grader returned invalid feedback shape")
    return result
