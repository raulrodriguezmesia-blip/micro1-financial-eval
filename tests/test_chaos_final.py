import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from mcp_server.chaos import ChaosEngine  # noqa: E402


def test_schema_drift_with_existing_field():
    """Cover line 99: mutated.pop(policy.target_field) when field exists."""
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    result = engine.apply("chaos_schema_drift", {"success": True, "target_currency": "USD"})
    assert "_contract_violation" in result
    assert "target_currency" not in result


def test_apply_fallback_return():
    """Cover line 135: final return payload fallback."""
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    # Monkeypatch a policy with an unhandled mode by directly calling apply
    # with a scenario_id that doesn't exist (returns payload unchanged)
    result = engine.apply("nonexistent_scenario_id", {"key": "value"})
    assert result == {"key": "value"}
