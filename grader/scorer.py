"""
grader/scorer.py — Scoring engine for micro1 Eval Hackathon.

Provides 0-100 partial scoring for AI model responses against task rubrics.
"""

import re
from typing import Any, Dict, List, Optional


def score_response(task_id: str, model_response: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    """Score a model response against a grading rubric.

    Args:
        task_id: The task identifier.
        model_response: The raw text response from the LLM.
        rubric: A dict with 'criteria' (list of dicts with 'name', 'weight', 'check').

    Returns:
        Dict with 'score' (0-100), 'max_score', 'breakdown' (list of criterion results),
        and 'passed' (bool, score >= 70).
    """
    criteria = rubric.get("criteria", [])
    if not criteria:
        return {"task_id": task_id, "score": 0, "max_score": 0, "breakdown": [], "passed": False}

    total_weight = sum(c.get("weight", 1) for c in criteria)
    earned = 0
    breakdown = []

    for criterion in criteria:
        name = criterion.get("name", "unnamed")
        weight = criterion.get("weight", 1)
        check_type = criterion.get("check", "contains")
        check_value = criterion.get("value", "")
        case_sensitive = criterion.get("case_sensitive", False)

        text = model_response if case_sensitive else model_response.lower()
        target = check_value if case_sensitive else check_value.lower()

        passed = False
        if check_type == "contains":
            passed = target in text
        elif check_type == "not_contains":
            passed = target not in text
        elif check_type == "regex":
            import re
            flags = 0 if case_sensitive else re.IGNORECASE
            passed = bool(re.search(check_value, model_response, flags))
        elif check_type == "count_min":
            passed = text.count(target) >= criterion.get("min_count", 1)
        elif check_type == "length_min":
            passed = len(model_response) >= criterion.get("min_length", 1)

        score_earned = weight if passed else 0
        earned += score_earned
        breakdown.append({
            "criterion": name,
            "weight": weight,
            "passed": passed,
            "score_earned": score_earned,
        })

    score = round((earned / total_weight) * 100, 1) if total_weight > 0 else 0
    return {
        "task_id": task_id,
        "score": score,
        "max_score": 100,
        "earned_weight": earned,
        "total_weight": total_weight,
        "breakdown": breakdown,
        "passed": score >= 70,
    }


def aggregate_scores(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate scores across multiple tasks."""
    if not results:
        return {"total_tasks": 0, "avg_score": 0, "passed": 0, "failed": 0, "scores": []}

    scores = [r.get("score", 0) for r in results]
    passed = sum(1 for r in results if r.get("passed", False))
    return {
        "total_tasks": len(results),
        "avg_score": round(sum(scores) / len(scores), 1),
        "passed": passed,
        "failed": len(results) - passed,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "scores": scores,
    }
