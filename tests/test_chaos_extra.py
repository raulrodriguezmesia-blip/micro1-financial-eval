import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from mcp_server.chaos import ChaosEngine, ChaosMode, ChaosPolicy  # noqa: E402


def test_applies_to_wildcard():
    policy = ChaosPolicy(target_tool="*")
    assert policy.applies_to("any_tool") is True


def test_applies_to_specific():
    policy = ChaosPolicy(target_tool="get_balance")
    assert policy.applies_to("get_balance") is True
    assert policy.applies_to("transfer_funds") is False


def test_rng_returns_random():
    policy = ChaosPolicy(seed=42)
    rng = policy.rng()
    assert rng is not None
    val = rng.randint(0, 100)
    assert 0 <= val <= 100


def test_schema_drift_with_target_field():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    # Find a schema drift scenario
    scenario_id = None
    for sid, policy in engine.by_id.items():
        if policy.mode == ChaosMode.SCHEMA_DRIFT:
            scenario_id = sid
            break
    if scenario_id:
        result = engine.apply(scenario_id, {"success": True, "amount": 100.0, "target_field": "value"})
        assert isinstance(result, dict)


def test_artificial_latency():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    scenario_id = None
    for sid, policy in engine.by_id.items():
        if policy.mode == ChaosMode.ARTIFICIAL_LATENCY:
            scenario_id = sid
            break
    if scenario_id:
        result = engine.apply(scenario_id, {"success": True})
        assert isinstance(result, dict)


def test_active_modes_valid():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    scenario_id = list(engine.by_id.keys())[0]
    modes = engine.active_modes(scenario_id)
    assert isinstance(modes, list)
    assert len(modes) >= 1


def test_active_modes_invalid():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    modes = engine.active_modes("nonexistent_scenario")
    assert modes == []


def test_none_mode_returns_payload():
    engine = ChaosEngine()
    result = engine.apply("nonexistent", {"key": "value"})
    assert result == {"key": "value"}


def test_false_success_mode():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    scenario_id = None
    for sid, policy in engine.by_id.items():
        if policy.mode == ChaosMode.FALSE_SUCCESS:
            scenario_id = sid
            break
    if scenario_id:
        result = engine.apply(scenario_id, {"success": False})
        assert result["success"] is True
        assert "_contract_violation" in result


def test_decoy_error_mode():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    scenario_id = None
    for sid, policy in engine.by_id.items():
        if policy.mode == ChaosMode.DECOY_ERROR:
            scenario_id = sid
            break
    if scenario_id:
        result = engine.apply(scenario_id, {"success": True})
        assert result["success"] is False
        assert "INSUFFICIENT_FUNDS" in result["error"]


def test_timeout_cascade_mode():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    scenario_id = None
    for sid, policy in engine.by_id.items():
        if policy.mode == ChaosMode.TIMEOUT_CASCADE:
            scenario_id = sid
            break
    if scenario_id:
        result = engine.apply(scenario_id, {"success": True})
        assert result["success"] is False
        assert "UPSTREAM_TIMEOUT" in result["error"]


def test_by_id_empty():
    engine = ChaosEngine()
    assert engine.by_id == {}


def test_chaos_mode_enum_values():
    assert ChaosMode.NONE.value == "NONE"
    assert ChaosMode.SCHEMA_DRIFT.value == "SCHEMA_DRIFT"
    assert ChaosMode.ARTIFICIAL_LATENCY.value == "ARTIFICIAL_LATENCY"
    assert ChaosMode.TRUNCATED_RESPONSE.value == "TRUNCATED_RESPONSE"
    assert ChaosMode.FALSE_SUCCESS.value == "FALSE_SUCCESS"
    assert ChaosMode.DECOY_ERROR.value == "DECOY_ERROR"
    assert ChaosMode.TIMEOUT_CASCADE.value == "TIMEOUT_CASCADE"


def test_chaos_policy_defaults():
    policy = ChaosPolicy()
    assert policy.mode == ChaosMode.NONE
    assert policy.target_tool == "*"
    assert policy.seed == 1337
    assert policy.target_field is None
    assert policy.delay_ms == 0
    assert policy.jitter_ms == 0
    assert policy.truncate_at == 50
    assert policy.depends_on is None
    assert policy.metadata == {}


def test_engine_from_file_loads_scenarios():
    engine = ChaosEngine.from_file("mcp_server/scenarios.json")
    assert len(engine.by_id) > 0
    assert len(engine.policies) > 0
