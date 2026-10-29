import pytest
"""
tests/test_server.py — Pruebas unitarias para mcp_server/server.py

Valida las herramientas MCP (get_balance, transfer_funds, convert_fx,
list_accounts, reset_state, activate_chaos, deactivate_chaos) y el
comportamiento del ChaosEngine integrado.
"""

import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

import mcp_server.server as server  # noqa: E402


def test_get_balance_existing():
    server.reset_state()
    result = server.get_balance("ACC_USD_001")
    assert result["success"] is True
    assert result["balance"] == 5000.0
    assert result["accountId"] == "ACC_USD_001"


def test_get_balance_nonexistent():
    server.reset_state()
    result = server.get_balance("ACC_NONEXISTENT")
    assert result["success"] is True
    assert result["balance"] == 0.0


def test_transfer_funds_success():
    server.reset_state()
    result = server.transfer_funds("ACC_USD_001", "ACC_USD_003", 1000.0)
    assert result["success"] is True
    assert result["amount"] == 1000.0
    assert result["newBalanceSrc"] == 4000.0


def test_transfer_funds_insufficient():
    server.reset_state()
    result = server.transfer_funds("ACC_USD_001", "ACC_USD_003", 99999.0)
    assert result["success"] is False
    assert result["error"] == "INSUFFICIENT_FUNDS"


def test_convert_fx():
    server.reset_state()
    result = server.convert_fx("USD", "EUR", 1000.0)
    assert result["success"] is True
    assert result["convertedAmount"] == 920.0
    assert result["rate"] == 0.92


def test_list_accounts():
    server.reset_state()
    result = server.list_accounts()
    assert result["success"] is True
    assert len(result["accounts"]) == 3
    ids = [a["accountId"] for a in result["accounts"]]
    assert "ACC_USD_001" in ids


def test_reset_state():
    server.reset_state()
    server.transfer_funds("ACC_USD_001", "ACC_USD_003", 1000.0)
    result = server.reset_state()
    assert result["success"] is True
    assert server._balances["ACC_USD_001"] == 5000.0


def test_activate_chaos_valid():
    result = server.activate_chaos("chaos_schema_drift")
    assert result["success"] is True
    assert result["scenario_id"] == "chaos_schema_drift"
    assert result["mode"] == "SCHEMA_DRIFT"
    server.deactivate_chaos()


def test_activate_chaos_invalid():
    result = server.activate_chaos("nonexistent_scenario")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_deactivate_chaos():
    server.activate_chaos("chaos_schema_drift")
    result = server.deactivate_chaos()
    assert result["success"] is True
    assert result["previous"] == "chaos_schema_drift"


def test_deactivate_chaos_when_none_active():
    server.deactivate_chaos()
    result = server.deactivate_chaos()
    assert result["success"] is True
    assert result["previous"] is None


def test_apply_chaos_schema_drift():
    server.reset_state()
    server.deactivate_chaos()
    server.activate_chaos("chaos_schema_drift")
    result = server.get_balance("ACC_USD_001")
    assert "_contract_violation" in result
    server.deactivate_chaos()


def test_apply_chaos_false_success():
    server.reset_state()
    server.deactivate_chaos()
    server.activate_chaos("chaos_false_success")
    result = server.transfer_funds("ACC_USD_001", "ACC_USD_003", 100.0)
    assert result["success"] is True
    assert "_contract_violation" in result
    server.deactivate_chaos()


def test_apply_chaos_decoy_error():
    server.reset_state()
    server.deactivate_chaos()
    server.activate_chaos("chaos_decoy_error")
    result = server.transfer_funds("ACC_USD_001", "ACC_USD_003", 100.0)
    assert result["success"] is False
    assert "INSUFFICIENT_FUNDS" in result["error"]
    server.deactivate_chaos()


def test_apply_chaos_timeout_cascade():
    server.reset_state()
    server.deactivate_chaos()
    server.activate_chaos("chaos_timeout_cascade")
    result = server.convert_fx("USD", "EUR", 100.0)
    assert result["success"] is False
    assert "UPSTREAM_TIMEOUT" in result["error"]
    server.deactivate_chaos()


def test_apply_chaos_truncated_response():
    server.reset_state()
    server.deactivate_chaos()
    server.activate_chaos("chaos_truncated_response")
    result = server.get_balance("ACC_USD_001")
    assert "__raw__" in result
    assert "_contract_violation" in result
    server.deactivate_chaos()


def test_no_chaos_returns_clean_payload():
    server.reset_state()
    server.deactivate_chaos()
    result = server.get_balance("ACC_USD_001")
    assert "_contract_violation" not in result
    assert "__raw__" not in result
    assert result["success"] is True


import pytest
import mcp_server.server as server


@pytest.fixture(autouse=True)
def reset_server_chaos_state():
    """Asegura que el estado global del escenario de caos se limpie antes y después de cada test."""
    if hasattr(server, "_active_scenario"):
        server._active_scenario = None
    yield
    if hasattr(server, "_active_scenario"):
        server._active_scenario = None
