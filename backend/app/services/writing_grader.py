"""
Real writing grader — runs entirely on a LOCAL model via Ollama.
No cloud API, no external network call, nothing leaves the machine.
Every call hits the local model live with the learner's actual
submitted text. No cached/canned responses.

Calibration: CEFR anchor descriptions are given explicitly so scoring
is consistent run-to-run, and a strictness mode lets the grading lean
lenient (encouraging, for beginners) or strict (closer to real exam
standards) without changing the underlying rubric dimensions.
"""
import json
from app.services.local_llm import local_llm_json_call

CEFR_ANCHORS = """CEFR level anchors for German writing (use these as ground truth, do not invent your own scale):
- A1 (0-39): Isolated words/phrases, frequent basic errors, minimal connectors, very short.
- A2 (40-54): Simple connected sentences, common everyday vocabulary, frequent but not blocking errors.
- B1 (55-69): Connected text on familiar topics, some complex sentences, errors present but rarely obscure meaning.
- B2 (70-84): Clear detailed text, varied vocabulary, good control of grammar with occasional slips.
- C1 (85-94): Well-structured, wide vocabulary, few errors, nuanced expression.
- C2 (95-100): Near-native precision, idiomatic, virtually error-free."""

STRICTNESS_MODES = {
    "lenient": "Grade encouragingly: give credit for communicated meaning even with errors, weight task achievement and effort, don't over-penalize minor spelling. Suitable for beginners building confidence.",
    "standard": "Grade fairly and evenly: follow the CEFR anchors closely, balanced between accuracy and communication.",
    "strict": "Grade like a real certified exam: apply CEFR anchors precisely, penalize grammar and spelling errors consistently, do not round up out of encouragement.",
}

def build_rubric(strictness: str = "standard") -> str:
    mode_instruction = STRICTNESS_MODES.get(strictness, STRICTNESS_MODES["standard"])
    return f"""You are a certified German language examiner grading a learner's
written German against the CEFR framework (A1-C2).

{CEFR_ANCHORS}

Grading mode: {mode_instruction}

Score on these dimensions, each 0-25 (total 0-100):
- Grammar accuracy (verb conjugation, case, word order)
- Vocabulary range and appropriateness for claimed level
- Coherence and structure
- Task achievement (did they answer/address the prompt)

If the text is not real German at all (random letters, another language,
gibberish), score near 0 and say so plainly in next_steps — do not
invent partial credit for non-German text.

Return ONLY valid JSON, no markdown fences, no preamble, in this exact shape:
{{
  "score": <int 0-100>,
  "cefr_estimate": "<A1|A2|B1|B2|C1|C2>",
  "grammar_errors": [{{"error": "<quoted fragment>", "correction": "<fix>", "explanation": "<why>"}}],
  "strengths": ["<short point>", ...],
  "next_steps": ["<short actionable point>", ...]
}}"""


def grade_writing(prompt_text: str, learner_text: str, strictness: str = "standard") -> dict:
    """
    Real, live local grading call. Raises on failure — caller must
    handle the real error state, not substitute a fake score.

    strictness: "lenient" | "standard" | "strict"
    """
    if not learner_text or not learner_text.strip():
        raise ValueError("Empty submission — nothing to grade")
    if strictness not in STRICTNESS_MODES:
        raise ValueError(f"Invalid strictness: {strictness}. Must be one of {list(STRICTNESS_MODES)}")

    messages = [
        {"role": "user", "content": f"Prompt: {prompt_text}\nLearner text: {learner_text}"}
    ]

    result = local_llm_json_call(system=build_rubric(strictness), messages=messages, max_tokens=1000)

    required = {"score", "cefr_estimate", "grammar_errors", "strengths", "next_steps"}
    if not required.issubset(result.keys()):
        raise RuntimeError(f"Grader response missing fields: {result.keys()}")
    if not isinstance(result["score"], int) or not 0 <= result["score"] <= 100:
        raise RuntimeError("Writing grader returned invalid score")
    if result["cefr_estimate"] not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        raise RuntimeError("Writing grader returned invalid CEFR estimate")
    if not all(isinstance(result[key], list) for key in ("grammar_errors", "strengths", "next_steps")):
        raise RuntimeError("Writing grader returned invalid feedback shape")
    return result
