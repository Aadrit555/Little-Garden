"""
Real reading comprehension grader — runs entirely on a LOCAL model
via Ollama. No cloud API. Compares learner's actual answer against
the real answer key stored in content_items.answer_key.
"""
from app.services.local_llm import local_llm_json_call

SYSTEM = """You grade a German learner's answer to a reading comprehension
question. You are given the expected answer (ground truth) and the
learner's actual answer. Judge whether the learner demonstrated real
comprehension, allowing for paraphrase, minor spelling issues, and
partial correctness.

Return ONLY valid JSON, no markdown fences:
{
  "correct": <true|false>,
  "partial_credit": <float 0.0-1.0>,
  "feedback": "<one sentence, in simple terms, on what was right/missed>"
}"""


def grade_reading_answer(question: str, expected_answer: str, learner_answer: str) -> dict:
    if not learner_answer or not learner_answer.strip():
        raise ValueError("Empty answer — nothing to grade")

    user_msg = (
        f"Question: {question}\n"
        f"Expected answer: {expected_answer}\n"
        f"Learner's answer: {learner_answer}"
    )

    result = local_llm_json_call(system=SYSTEM, messages=[{"role": "user", "content": user_msg}], max_tokens=300)

    required = {"correct", "partial_credit", "feedback"}
    if not required.issubset(result.keys()):
        raise RuntimeError(f"Reading grader response missing fields: {result.keys()}")
    if not isinstance(result["correct"], bool):
        raise RuntimeError("Reading grader returned invalid correct flag")
    if not isinstance(result["partial_credit"], (int, float)) or not 0 <= result["partial_credit"] <= 1:
        raise RuntimeError("Reading grader returned invalid partial credit")
    if not isinstance(result["feedback"], str):
        raise RuntimeError("Reading grader returned invalid feedback")
    return result


def score_reading_session(answers: list[dict]) -> dict:
    """
    answers: list of {"question": str, "expected": str, "learner": str}
    Aggregates real per-answer grading into a session score.
    Every answer graded live on the local model — no shortcuts.
    """
    if not answers:
        raise ValueError("No answers submitted")

    graded = [grade_reading_answer(a["question"], a["expected"], a["learner"]) for a in answers]
    total_credit = sum(g["partial_credit"] for g in graded)
    pct = round((total_credit / len(graded)) * 100, 1)

    return {"score": pct, "per_question": graded}
