"""
tests/test_grade.py — Pruebas unitarias para grader/grade.py

Valida que el orquestador del eval procese todas las tareas, aplique caos
y produzca un reporte JSON con executionProof para cada tarea.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.grade import run_eval  # noqa: E402


def test_run_eval_produces_json_with_execution_proof(tmp_path: Path) -> None:
    tasks_dir = Path(__file__).resolve().parent.parent / "tasks"
    output = tmp_path / "results" / "grade_results.json"

    summary = run_eval(tasks_dir, output)

    assert output.exists()
    assert summary["total"] == 10
    assert summary["approved"] + summary["rejected"] == 10
    assert summary["errors"] == 0

    data = json.loads(output.read_text(encoding="utf-8"))
    for entry in data["results"]:
        assert "task_id" in entry
        assert "status" in entry
        assert entry["status"] in ("APPROVED", "REJECTED")
        proof = entry["execution_proof"]
        assert "validations_passed" in proof
        assert "timestamp" in proof
        assert "guardrail_triggered" in proof
        assert isinstance(proof["guardrail_triggered"], bool)
