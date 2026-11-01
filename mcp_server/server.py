"""
Servidor MCP FastMCP con herramientas financieras y soporte de caos.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from .chaos import ChaosEngine, ChaosMode

mcp = FastMCP("financial-mcp-server")

_balances: Dict[str, float] = {
    "ACC_USD_001": 5000.0,
    "ACC_EUR_002": 3000.0,
    "ACC_USD_003": 20000.0,
}

_engine = ChaosEngine()
_active_scenario: Optional[str] = None

# Rate limiter simple en memoria
_rate_buckets: dict[str, deque] = defaultdict(deque)
_RATE_LIMIT = 1000  # peticiones por minuto
_RATE_WINDOW = 60.0


def _check_rate_limit(tool_name: str) -> None:
    now = time.time()
    bucket = _rate_buckets[tool_name]
    while bucket and bucket[0] < now - _RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        raise RuntimeError("RATE_LIMIT_EXCEEDED")
    bucket.append(now)


def _apply_chaos(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _active_scenario:
        engine = ChaosEngine.from_file()
        return engine.apply(_active_scenario, payload)
    return payload


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def get_balance(accountId: str) -> Dict[str, Any]:
    """Devuelve el saldo de una cuenta."""
    try:
        _check_rate_limit("get_balance")
        payload = {
            "accountId": accountId,
            "currency": "USD",
            "balance": _balances.get(accountId, 0.0),
            "success": True,
        }
        return _apply_chaos("get_balance", payload)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False})
def transfer_funds(from_: str, to: str, amount: float) -> Dict[str, Any]:
    """Transfiere fondos entre cuentas."""
    try:
        _check_rate_limit("transfer_funds")
        from_balance = _balances.get(from_, 0.0)
        if from_balance < amount:
            payload = {
                "success": False,
                "error": "INSUFFICIENT_FUNDS",
                "from": from_,
                "to": to,
                "amount": amount,
            }
        else:
            _balances[from_] = from_balance - amount
            _balances[to] = _balances.get(to, 0.0) + amount
            payload = {
                "success": True,
                "from": from_,
                "to": to,
                "amount": amount,
                "newBalanceSrc": _balances[from_],
            }
        return _apply_chaos("transfer_funds", payload)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def convert_fx(fromCurrency: str, toCurrency: str, amount: float) -> Dict[str, Any]:
    """Convierte una cantidad entre monedas (simulado)."""
    try:
        _check_rate_limit("convert_fx")
        payload = {
            "success": True,
            "fromCurrency": fromCurrency,
            "toCurrency": toCurrency,
            "amount": amount,
            "convertedAmount": amount * 0.92,
            "rate": 0.92,
        }
        return _apply_chaos("convert_fx", payload)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
def list_accounts() -> Dict[str, Any]:
    """Lista las cuentas disponibles."""
    try:
        _check_rate_limit("list_accounts")
        payload = {
            "success": True,
            "accounts": [{"accountId": k, "currency": "USD", "balance": v} for k, v in _balances.items()],
        }
        return _apply_chaos("list_accounts", payload)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False})
def reset_state() -> Dict[str, Any]:
    """Reinicia el estado en memoria (útil para pruebas)."""
    try:
        _check_rate_limit("reset_state")
        _balances.clear()
        _balances.update({"ACC_USD_001": 5000.0, "ACC_EUR_002": 3000.0, "ACC_USD_003": 20000.0})
        return {"success": True, "message": "state reset"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False})
def activate_chaos(scenario_id: str) -> Dict[str, Any]:
    """Activa un escenario de caos por su id."""
    try:
        _check_rate_limit("activate_chaos")
        global _active_scenario
        engine = ChaosEngine.from_file()
        if scenario_id not in engine.by_id:
            return {"success": False, "error": f"scenario '{scenario_id}' not found"}
        _active_scenario = scenario_id
        return {"success": True, "scenario_id": scenario_id, "mode": engine.by_id[scenario_id].mode.value}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False})
def deactivate_chaos() -> Dict[str, Any]:
    """Desactiva cualquier escenario de caos activo."""
    try:
        _check_rate_limit("deactivate_chaos")
        global _active_scenario
        previous = _active_scenario
        _active_scenario = None
        return {"success": True, "previous": previous}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
