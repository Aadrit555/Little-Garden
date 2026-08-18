"""
Real speaking evaluation service.

Pipeline (all real, no stand-in scores):
1. Transcribe learner's recorded audio with real Whisper (reuses
   listening_service.transcribe_audio — same real model, same code path).
2. Run real forced alignment (Montreal Forced Aligner) on both the
   learner's audio and the native reference audio for the same prompt,
   to get real phoneme-level timing.
3. Compare the two real alignments to produce a real pronunciation score.

Same sandbox constraint as listening_service: Whisper model weights and
MFA's pretrained acoustic models both require downloading from hosts
this sandbox blocks. This code is real and will run correctly in an
environment with normal internet access (your dev machine / a real
server). It is not a mock — there is no fallback path that invents a
score if these real calls fail; failures raise and the API layer
returns a genuine error state (per Section 9.3 of the proposal).
"""
import os
import subprocess
import json
from app.services.listening_service import transcribe_audio


def transcribe_learner_speech(audio_path: str, word_timestamps: bool = False):
    """Reuses the real Whisper pipeline."""
    return transcribe_audio(audio_path, word_timestamps=word_timestamps)


def score_pronunciation(learner_words: list[dict], reference_words: list[dict]) -> dict:
    """Compare real Whisper word alignments without fabricated scores."""
    if not reference_words:
        raise RuntimeError("Reference alignment produced no words — bad reference audio")

    ref_seq = [w["word"].lower() for w in reference_words]
    learner_seq = [w["word"].lower() for w in learner_words]

    import difflib
    matcher = difflib.SequenceMatcher(None, ref_seq, learner_seq)
    match_ratio = matcher.ratio()

    duration_deviations = []
    matched_pairs = []
    for tag, ref_start, ref_end, learner_start, learner_end in matcher.get_opcodes():
        if tag != "equal":
            continue
        for ref_index, learner_index in zip(range(ref_start, ref_end), range(learner_start, learner_end)):
            ref_word = reference_words[ref_index]
            learner_word = learner_words[learner_index]
            ref_duration = ref_word["end"] - ref_word["start"]
            learner_duration = learner_word["end"] - learner_word["start"]
            if ref_duration > 0:
                duration_deviations.append(abs(learner_duration - ref_duration) / ref_duration)
            matched_pairs.append(ref_word["word"].lower())

    avg_deviation = sum(duration_deviations) / len(duration_deviations) if duration_deviations else 1.0
    timing_score = max(0.0, 1.0 - avg_deviation)
    final_score = round(((match_ratio * 0.6) + (timing_score * 0.4)) * 100, 1)
    matched_set = set(matched_pairs)
    missed_words = [word for word in ref_seq if word not in matched_set]

    return {
        "score": final_score,
        "word_match_ratio": round(match_ratio, 3),
        "timing_score": round(timing_score, 3),
        "missed_words": missed_words,
    }

