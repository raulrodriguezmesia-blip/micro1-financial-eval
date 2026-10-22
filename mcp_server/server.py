"""
Servidor MCP FastMCP con herramientas financieras y soporte de caos.

Expone herramientas:
- get_balance(accountId) -> saldo de cuenta
- transfer_funds(from, to, amount) -> transferencia
- convert_fx(fromCurrency, toCurrency, amount) -> conversión FX
- list_accounts() -> lista de cuentas
- reset_state() -> reinicia estado (pruebas)
- activate_chaos(scenario_id) -> activa un escenario de caos
- deactivate_chaos() -> desactiva el caos
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastmcp import FastMCP

from chaos import ChaosEngine, ChaosMode

mcp = FastMCP("financial-mcp-server")

# Estado en memoria (solo para el eval simulado)
_balances: Dict[str, float] = {
    "ACC_USD_001": 5000.0,
    "ACC_EUR_002": 3000.0,
    "ACC_USD_003": 20000.0,
}

_engine = ChaosEngine()
_active_scenario: Optional[str] = None


def _active_tool_name() -> str:
    return ""


@mcp.tool()
def get_balance(accountId: str) -> Dict[str, Any]:
    """Devuelve el saldo de una cuenta."""
    payload = {
        "accountId": accountId,
        "currency": "USD",
        "balance": _balances.get(accountId, 0.0),
        "success": True,
    }
    return _apply_chaos("get_balance", payload)


@mcp.tool()
def transfer_funds(from_: str, to: str, amount: float) -> Dict[str, Any]:
    """Transfiere fondos entre cuentas."""
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


@mcp.tool()
def convert_fx(fromCurrency: str, toCurrency: str, amount: float) -> Dict[str, Any]:
    """Convierte una cantidad entre monedas (simulado)."""
    payload = {
        "success": True,
        "fromCurrency": fromCurrency,
        "toCurrency": toCurrency,
        "amount": amount,
        "convertedAmount": amount * 0.92,
        "rate": 0.92,
    }
    return _apply_chaos("convert_fx", payload)


@mcp.tool()
def list_accounts() -> Dict[str, Any]:
    """Lista las cuentas disponibles."""
    payload = {
        "success": True,
        "accounts": [{"accountId": k, "currency": "USD", "balance": v} for k, v in _balances.items()],
    }
    return _apply_chaos("list_accounts", payload)


@mcp.tool()
def reset_state() -> Dict[str, Any]:
    """Reinicia el estado en memoria (útil para pruebas)."""
    _balances.clear()
    _balances.update({"ACC_USD_001": 5000.0, "ACC_EUR_002": 3000.0, "ACC_USD_003": 20000.0})
    return {"success": True, "message": "state reset"}


@mcp.tool()
def activate_chaos(scenario_id: str) -> Dict[str, Any]:
    """Activa un escenario de caos por su id."""
    global _active_scenario
    engine = ChaosEngine.from_file()
    if scenario_id not in engine.by_id:
        return {"success": False, "error": f"scenario '{scenario_id}' not found"}
    _active_scenario = scenario_id
    return {"success": True, "scenario_id": scenario_id, "mode": engine.by_id[scenario_id].mode.value}


@mcp.tool()
def deactivate_chaos() -> Dict[str, Any]:
    """Desactiva cualquier escenario de caos activo."""
    global _active_scenario
    previous = _active_scenario
    _active_scenario = None
    return {"success": True, "previous": previous}


def _apply_chaos(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _active_scenario:
        return _engine.apply(_active_scenario, payload)
    return payload


if __name__ == "__main__":
    mcp.run(transport="stdio")
