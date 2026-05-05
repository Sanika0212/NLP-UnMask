"""
Socratic Purity Metric.

Two components:
  1. Rule-based: response ends with "?", no direct answer leak (from answer_leak.py)
  2. LLM-as-Judge: Mercury-2 rates the response 1-5 on a Socratic quality rubric

Combined score = (llm_score / 5.0) penalized by rule violations.
Target: ≥ 4.0 / 5.0 average.
"""
from __future__ import annotations

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_JUDGE_PROMPT = """\
You are evaluating an AI tutor's response for Socratic quality.

The tutor knows the correct answer but should NOT reveal it directly.
Instead, it should ask a question that guides the student toward discovering the answer themselves.

Student asked: {question}
Tutor responded: {response}
Gold answer (what the tutor knows but should not say): {gold_answer}

Rate the tutor's response on this 1-5 scale:

5 — Perfect Socratic: asks a targeted question that guides discovery; gold answer completely absent; student must think to answer
4 — Good Socratic: question guides toward answer; minor partial info slipped but no direct reveal
3 — Weak Socratic: question present but contains hints that make the answer obvious
2 — Near-leak: response contains most of the answer, framed as a question (e.g., "Isn't it the axillary nerve?")
1 — Direct answer: gold answer stated outright, regardless of whether it ends with "?"

Respond with ONLY: <score> <one-sentence-reason>
Example: 4 The question targets the right anatomical concept without naming the nerve directly.
"""


def llm_judge(
    question: str,
    response: str,
    gold_answer: str,
) -> tuple[float, str]:
    """Returns (score 1-5, reason)."""
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    import yaml
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", cfg["llm"]["model"]),
        messages=[{
            "role": "user",
            "content": _JUDGE_PROMPT.format(
                question=question,
                response=response,
                gold_answer=gold_answer,
            ),
        }],
        max_tokens=80,
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    try:
        parts = text.split(" ", 1)
        score = float(parts[0])
        reason = parts[1] if len(parts) > 1 else ""
    except (ValueError, IndexError):
        score = 3.0
        reason = text

    return score, reason


def socratic_purity_score(
    question: str,
    response: str,
    gold_answer: str,
    leaked: bool,
    ends_with_question: bool,
    soft_flag: bool = False,
) -> dict:
    """
    Combined Socratic purity score.
    - confirmed leak (both layers): hard cap at 2.0
    - soft flag (one layer only): -0.5 penalty
    - no "?": -1.0 penalty
    LLM judge is the primary signal.
    """
    llm_score, reason = llm_judge(question, response, gold_answer)

    penalty_reason = None
    if leaked:
        # Both keyword AND semantic fired — confirmed leak
        final_score = min(llm_score, 2.0)
        penalty_reason = "confirmed answer leak (both layers)"
    elif soft_flag:
        # Only one layer fired — possible over-eagerness, soft penalty
        final_score = max(1.0, llm_score - 0.5)
        penalty_reason = "soft leak flag (single layer)"
    elif not ends_with_question:
        final_score = max(1.0, llm_score - 1.0)
        penalty_reason = "response does not end with ?"
    else:
        final_score = llm_score

    return {
        "llm_score": llm_score,
        "final_score": final_score,
        "llm_reason": reason,
        "penalty": penalty_reason,
        "passed": final_score >= 4.0,
    }
