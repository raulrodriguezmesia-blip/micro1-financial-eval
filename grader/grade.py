"""
grader/grade.py — Orquestador del eval micro1 (sin servidor vivo requerido).

Lee tasks/task_*.yaml, construye payloads base embebidos, aplica caos determinista
usando ChaosEngine, ejecuta validate_task (invariantes O(1)) y emite
results/grade_results.json con executionProof por tarea.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.invariants import validate_task  # noqa: E402
from mcp_server.chaos import ChaosEngine, ChaosMode  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Payloads base por tarea (sin servidor MCP vivo)
_TASK_PAYLOADS: Dict[str, Dict[str, Any]] = {
    "task_01": {
        "success": True,
        "from": "ACC_USD_001",
        "to": "ACC_EUR_002",
        "amount": 1000.0,
        "requestId": "550e8400-e29b-41d4-a716-446655440000",
        "newBalanceSrc": 4000.0,
    },
    "task_02": {
        "success": False,
        "error": "REJECTED: El monto excede el límite de la política de tesorería.",
        "requestId": "550e8400-e29b-41d4-a716-446655440001",
        "amount": 75000.0,
    },
    "task_03": {
        "success": False,
        "error": "REJECTED: Balance insuficiente para conversión FX.",
        "requestId": "550e8400-e29b-41d4-a716-446655440002",
        "amount": 4000.0,
        "balance": 3000.0,
    },
    "task_04": {
        "success": True,
        "fromCurrency": "USD",
        "amount": 1000.0,
        "requestId": "550e8400-e29b-41d4-a716-446655440003",
    },
    "task_05": {
        "success": True,
        "accountId": "ACC_USD_001",
        "currency": "USD",
        "balance": 5000.0,
    },
    "task_06": {
        "__raw__": '{"partial": true}',
        "_contract_violation": "truncated JSON payload",
    },
    "task_07": {
        "success": True,
        "amount": 500.0,
        "requestId": "550e8400-e29b-41d4-a716-446655440004",
        "newBalanceSrc": 4500.0,
    },
    "task_08": {
        "success": True,
        "duplicate": True,
        "message": "Request already processed (idempotency)",
        "requestId": "550e8400-e29b-41d4-a716-446655440005",
    },
    "task_09": {
        "success": False,
        "error": "INSUFFICIENT_FUNDS: balance below requested amount",
        "requestId": "550e8400-e29b-41d4-a716-446655440006",
    },
    "task_10": {
        "success": False,
        "error": "UPSTREAM_TIMEOUT: dependency 'get_fx_rate' did not respond",
        "requestId": "550e8400-e29b-41d4-a716-446655440007",
    },
}

_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "task_01": ["from", "to", "amount", "requestId", "newBalanceSrc"],
    "task_02": ["requestId", "error"],
    "task_03": ["requestId", "error"],
    "task_04": ["fromCurrency", "toCurrency", "amount", "requestId"],
    "task_05": ["accountId", "currency", "balance"],
    "task_06": [],
    "task_07": ["amount", "requestId", "newBalanceSrc"],
    "task_08": ["requestId"],
    "task_09": ["requestId", "error"],
    "task_10": ["requestId", "error"],
}

_TOOL_NAME: Dict[str, str] = {
    "task_01": "transfer_funds",
    "task_02": "transfer_funds",
    "task_03": "convert_fx",
    "task_04": "convert_fx",
    "task_05": "get_balance",
    "task_06": "get_balance",
    "task_07": "transfer_funds",
    "task_08": "transfer_funds",
    "task_09": "transfer_funds",
    "task_10": "convert_fx",
}


def run_eval(tasks_dir: Path, output_path: Path) -> Dict[str, Any]:
    engine = ChaosEngine()
    task_files = sorted(tasks_dir.glob("task_*.yaml"))

    results: List[Dict[str, Any]] = []
    for task_file in task_files:
        task = _load_yaml(task_file)
        task_id = task_file.stem
        scenario_id = task.get("scenario_id") or ""
        chaos_mode = task.get("chaos_mode") or "NONE"

        base_payload = _TASK_PAYLOADS.get(task_id, {})
        mutated = engine.apply(scenario_id, dict(base_payload))

        request_id = mutated.get("requestId")
        amount = mutated.get("amount")
        balance = mutated.get("balance")
        required_fields = _REQUIRED_FIELDS.get(task_id, task.get("required_fields", []))
        tool_name = _TOOL_NAME.get(task_id)

        validation = validate_task(
            task_id=task_id,
            scenario_id=scenario_id,
            chaos_mode=chaos_mode,
            response=mutated,
            request_id=request_id,
            amount=amount,
            balance=balance,
            required_fields=required_fields,
            idempotency_seen=set(),
            tool_name=tool_name,
        )

        results.append(
            {
                "task_id": task_id,
                "task_def": task_file.name,
                "scenario_id": scenario_id,
                "chaos_mode": chaos_mode,
                "status": validation.status,
                "rejected_reason": None if validation.status == "APPROVED" else validation.message,
                "execution_proof": validation.execution_proof.to_dict(),
                "mutated_payload": mutated,
                "error": None,
            }
        )

    summary = {
        "eval": "MCP Contract Hallucination Eval",
        "total": len(results),
        "approved": sum(1 for r in results if r["status"] == "APPROVED"),
        "rejected": sum(1 for r in results if r["status"] == "REJECTED"),
        "errors": sum(1 for r in results if r.get("error")),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    return summary


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
            return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_simple_yaml(path)


def _parse_simple_yaml(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="micro1 Eval: MCP Contract Hallucination")
    parser.add_argument("--tasks-dir", default="tasks", help="Directorio con task_*.yaml")
    parser.add_argument("--output", default="results/grade_results.json", help="Ruta de salida JSON")
    args = parser.parse_args()

    tasks_dir = Path(args.tasks_dir).resolve()
    output_path = Path(args.output).resolve()

    files = list(tasks_dir.glob("task_*.yaml"))
    print(f"Running eval on {len(files)} tasks...")
    summary = run_eval(tasks_dir, output_path)
    print(
        f"Summary: {summary['approved']}/{summary['total']} approved, "
        f"{summary['rejected']} rejected, {summary['errors']} errors"
    )
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
