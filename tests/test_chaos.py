"""
tests/test_chaos.py — Pruebas unitarias para mcp_server/chaos.py

Valida que cada modo de mutación del ChaosEngine sea determinista y
reproducible, y que no altere el payload original cuando el modo es NONE.
"""

from __future__ import annotations

import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from mcp_server.chaos import ChaosEngine, ChaosMode  # noqa: E402


def _payload() -> dict:
    return {"success": True, "amount": 1000.0, "requestId": "abc-123"}


def test_none_mode_returns_payload_unchanged() -> None:
    engine = ChaosEngine()
    result = engine.apply("nonexistent", _payload())
    assert result == _payload()


def test_schema_drift_removes_target_field() -> None:
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    result = engine.apply("chaos_schema_drift", _payload())
    assert "_contract_violation" in result
    assert "missing required field" in result["_contract_violation"]


def test_false_success_sets_success_true() -> None:
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    payload = {"success": False, "error": "boom"}
    result = engine.apply("chaos_false_success", dict(payload))
    assert result["success"] is True
    assert "_contract_violation" in result


def test_decoy_error_sets_success_false() -> None:
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    payload = {"success": True}
    result = engine.apply("chaos_decoy_error", dict(payload))
    assert result["success"] is False
    assert "_contract_violation" in result


def test_timeout_cascade_mentions_dependency() -> None:
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    result = engine.apply("chaos_timeout_cascade", _payload())
    assert result["success"] is False
    assert "UPSTREAM_TIMEOUT" in result["error"]


def test_truncated_response_cuts_payload() -> None:
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    result = engine.apply("chaos_truncated_response", _payload())
    assert "__raw__" in result
    assert "_contract_violation" in result


def test_determinism_same_seed_same_output() -> None:
    p1 = ChaosEngine.from_file("mcp_server/scenarios.json").apply(
        "chaos_schema_drift", _payload()
    )
    p2 = ChaosEngine.from_file("mcp_server/scenarios.json").apply(
        "chaos_schema_drift", _payload()
    )
    assert p1 == p2
