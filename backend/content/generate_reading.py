"""
Generate reviewed-gated learner content with local LLM.

Supports reading passages and writing prompts. No learner-facing sample
sentences are stored in source code. Generated rows remain pending until
human review approves them.
"""
import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.base import SessionLocal, Base, engine
from app.models.db_models import ContentItem, Skill, CEFRLevel
from app.services.local_llm import local_llm_json_call


READING_SYSTEM = """Generate one natural German reading-comprehension item for a language learner.
Respect requested CEFR level. Use varied topics and vocabulary suitable for that level.
Return ONLY valid JSON:
{
  "passage": "<natural German passage>",
  "questions": [
    {"question": "<German comprehension question>", "expected_answer": "<correct short answer>"},
    {"question": "<German comprehension question>", "expected_answer": "<correct short answer>"}
  ]
}
Do not mention generation, CEFR, prompts, or answer keys in the passage."""

WRITING_SYSTEM = """Generate one natural German writing task for a language learner.
Respect requested CEFR level. Use varied real-world communication tasks and enough
specificity that learner responses can be graded consistently.
Return ONLY valid JSON:
{"prompt": "<German writing task>"}
Do not include a model answer."""

GENERATORS = {
    Skill.reading: READING_SYSTEM,
    Skill.writing: WRITING_SYSTEM,
}


def _clean_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Generation response has empty {field}")
    return value.strip()


def generate_one(skill: Skill, level: CEFRLevel) -> dict:
    system = GENERATORS[skill]
    result = local_llm_json_call(
        system=system,
        messages=[{"role": "user", "content": f"Generate one {skill.value} item at CEFR level {level.value}."}],
        max_tokens=700,
    )
    if skill == Skill.reading:
        if not {"passage", "questions"}.issubset(result.keys()) or not isinstance(result["questions"], list):
            raise RuntimeError(f"Generation response missing reading fields: {result.keys()}")
        passage = _clean_text(result["passage"], "passage")
        questions = []
        seen = set()
        for question in result["questions"]:
            if not isinstance(question, dict):
                continue
            q = _clean_text(question.get("question"), "question")
            answer = _clean_text(question.get("expected_answer"), "expected_answer")
            if q in seen:
                continue
            seen.add(q)
            questions.append({"question": q, "expected_answer": answer})
        if len(questions) < 2:
            raise RuntimeError("Generation response must contain at least two unique reading questions")
        return {"passage": passage, "questions": questions}

    if "prompt" not in result:
        raise RuntimeError(f"Generation response missing writing fields: {result.keys()}")
    return {"prompt": _clean_text(result["prompt"], "prompt")}


def create_item(skill: Skill, level: CEFRLevel, generated: dict) -> ContentItem:
    if skill == Skill.reading:
        answer_key = {
            q["question"]: q["expected_answer"]
            for q in generated["questions"]
        }
        return ContentItem(
            skill=skill,
            level=level,
            text_content=generated["passage"],
            answer_key=json.dumps(answer_key, ensure_ascii=False),
            source="local-llm-generated",
            reviewed="pending",
        )

    return ContentItem(
        skill=skill,
        level=level,
        text_content=generated["prompt"],
        source="local-llm-generated",
        reviewed="pending",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True, choices=["reading", "writing", "all"])
    parser.add_argument("--level", required=True, choices=[l.value for l in CEFRLevel])
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    level = CEFRLevel(args.level)
    skills = [Skill.reading, Skill.writing] if args.skill == "all" else [Skill(args.skill)]

    total_created = 0
    for skill in skills:
        created = 0
        for index in range(args.count):
            try:
                generated = generate_one(skill, level)
                db.add(create_item(skill, level, generated))
                created += 1
                total_created += 1
            except Exception as exc:
                print(f"Generation {skill.value} {index + 1} failed (real error, skipping): {exc}")
        print(f"Generated {created} real {skill.value} items at {level.value}, status=pending.")

    db.commit()
    db.close()
    print(f"Generated {total_created} real reading/writing items at {level.value}, status=pending.")
    print("Run review_queue.py to review and approve before learner exposure.")
