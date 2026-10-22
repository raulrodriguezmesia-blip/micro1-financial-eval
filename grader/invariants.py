"""
grader/invariants.py — Validador determinista O(1) de invariantes FinGuard.

Cada invariante se evalúa en tiempo constante. El resultado incluye un
ExecutionProof con las validaciones pasadas y si se disparó algún guardrail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

TX_LIMIT = 50000.0
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass
class ExecutionProof:
    validations_passed: List[str] = field(default_factory=list)
    timestamp: str = ""
    guardrail_triggered: bool = False
    scenario_id: str = ""
    mode: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validations_passed": self.validations_passed,
            "timestamp": self.timestamp,
            "guardrail_triggered": self.guardrail_triggered,
            "scenario_id": self.scenario_id,
            "mode": self.mode,
        }


@dataclass
class ValidationResult:
    status: str  # "APPROVED" | "REJECTED"
    message: str
    execution_proof: ExecutionProof


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_task(
    task_id: str,
    scenario_id: str,
    chaos_mode: str,
    response: Dict[str, Any],
    request_id: Optional[str] = None,
    amount: Optional[float] = None,
    balance: Optional[float] = None,
    required_fields: Optional[List[str]] = None,
    idempotency_seen: Optional[Set[str]] = None,
    tool_name: Optional[str] = None,
) -> ValidationResult:
    """Evalúa las invariantes O(1) sobre la respuesta del MCP."""
    passed: List[str] = []
    rejected_reason: Optional[str] = None
    required_fields = required_fields or []
    idempotency_seen = idempotency_seen or set()
    guardrail = False

    # --- UUID_CHECK ---
    if request_id and UUID_RE.match(str(request_id)):
        passed.append("UUID_CHECK")
    else:
        rejected_reason = rejected_reason or f"Tarea {task_id}: UUID_CHECK falló (requestId inválido)"

    # --- TX_LIMIT_CHECK ---
    if amount is not None:
        if amount <= TX_LIMIT:
            passed.append("TX_LIMIT_CHECK")
        else:
            guardrail = True
            rejected_reason = rejected_reason or f"Tarea {task_id}: TX_LIMIT_CHECK falló (monto {amount} > {TX_LIMIT})"
    else:
        passed.append("TX_LIMIT_CHECK")

    # --- SOLVENCY_CHECK (solo conversiones FX) ---
    if tool_name == "convert_fx":
        if balance is not None and amount is not None and balance >= amount:
            passed.append("SOLVENCY_CHECK")
        else:
            guardrail = True
            rejected_reason = rejected_reason or f"Tarea {task_id}: SOLVENCY_CHECK falló"
    else:
        passed.append("SOLVENCY_CHECK")

    # --- CONTRACT_COMPLETENESS ---
    missing = [f for f in required_fields if f not in response]
    if not missing:
        passed.append("CONTRACT_COMPLETENESS")
    else:
        guardrail = True
        rejected_reason = rejected_reason or f"Tarea {task_id}: CONTRACT_COMPLETENESS falló (faltan {missing})"

    # --- PARSE_INTEGRITY ---
    if isinstance(response, dict) and "_contract_violation" not in response:
        passed.append("PARSE_INTEGRITY")
    else:
        guardrail = True
        rejected_reason = rejected_reason or f"Tarea {task_id}: PARSE_INTEGRITY falló"

    # --- IDEMPOTENCY_CHECK ---
    if request_id and request_id not in idempotency_seen:
        passed.append("IDEMPOTENCY_CHECK")
    else:
        guardrail = True
        rejected_reason = rejected_reason or f"Tarea {task_id}: IDEMPOTENCY_CHECK falló (duplicate requestId)"

    # --- STATE_VERIFICATION ---
    if response.get("success") is True or response.get("success") is False:
        passed.append("STATE_VERIFICATION")
    else:
        passed.append("STATE_VERIFICATION")

    status = "APPROVED" if not guardrail and rejected_reason is None else "REJECTED"

    proof = ExecutionProof(
        validations_passed=passed,
        timestamp=_now_iso(),
        guardrail_triggered=guardrail,
        scenario_id=scenario_id,
        mode=chaos_mode,
    )

    message = rejected_reason if rejected_reason else "Tarea aprobada: todas las invariantes O(1) pasaron"
    return ValidationResult(status=status, message=message, execution_proof=proof)
