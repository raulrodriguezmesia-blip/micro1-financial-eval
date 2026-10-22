"""
ChaosEngine — Inyección determinista de fallos en respuestas MCP.

Cada mutación es determinista y reproducible: dado el mismo (tool, payload, seed)
produce exactamente el mismo output corrupto. Requisito duro del rubric micro1:
"the grader is reliable and doesn't produce false passes or false fails".
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChaosMode(str, Enum):
    """Modos de fallo inyectables en el canal de respuestas MCP."""

    NONE = "NONE"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    ARTIFICIAL_LATENCY = "ARTIFICIAL_LATENCY"
    TRUNCATED_RESPONSE = "TRUNCATED_RESPONSE"
    FALSE_SUCCESS = "FALSE_SUCCESS"
    DECOY_ERROR = "DECOY_ERROR"
    TIMEOUT_CASCADE = "TIMEOUT_CASCADE"


@dataclass
class ChaosPolicy:
    """
    Política de caos aplicada a una tool concreta.

    mode        : modo de mutación a aplicar.
    target_tool : tool sobre la que se aplica ("*" aplica a todas).
    seed        : semilla del PRNG -> comportamiento reproducible.
    target_field: campo a eliminar en SCHEMA_DRIFT.
    delay_ms    : retardo base en ARTIFICIAL_LATENCY.
    jitter_ms   : variación aleatoria (acotada, determinista por seed).
    truncate_at : número de bytes en TRUNCATED_RESPONSE.
    depends_on  : tool de la que depende en TIMEOUT_CASCADE.
    """

    mode: ChaosMode = ChaosMode.NONE
    target_tool: str = "*"
    seed: int = 1337
    target_field: Optional[str] = None
    delay_ms: int = 0
    jitter_ms: int = 0
    truncate_at: int = 50
    depends_on: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def applies_to(self, tool_name: str) -> bool:
        return self.target_tool in ("*", tool_name)

    def rng(self) -> random.Random:
        """PRNG determinista: misma semilla -> misma secuencia."""
        return random.Random(self.seed)


class ChaosEngine:
    def __init__(self, policies: Optional[List[ChaosPolicy]] = None) -> None:
        self.policies: List[ChaosPolicy] = policies or []
        self.by_id: Dict[str, ChaosPolicy] = {p.metadata.get("id", ""): p for p in self.policies}

    @classmethod
    def from_file(cls, scenarios_path: str = "mcp_server/scenarios.json") -> "ChaosEngine":
        with open(scenarios_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        policies: List[ChaosPolicy] = []
        for spec in raw.get("scenarios", []):
            policies.append(
                ChaosPolicy(
                    mode=ChaosMode(spec.get("mode", "NONE")),
                    target_tool=spec.get("target_tool", "*"),
                    seed=int(spec.get("seed", 1337)),
                    target_field=spec.get("field"),
                    delay_ms=int(spec.get("delay_ms", 0)),
                    jitter_ms=int(spec.get("jitter_ms", 0)),
                    truncate_at=int(spec.get("truncate_at", 50)),
                    depends_on=spec.get("depends_on"),
                    metadata={"id": spec.get("id", ""), "description": spec.get("description", "")},
                )
            )
        return cls(policies)

    def apply(self, scenario_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica el escenario de caos al payload y devuelve el mutado."""
        policy = self.by_id.get(scenario_id)
        if not policy or policy.mode == ChaosMode.NONE:
            return payload

        if policy.mode == ChaosMode.SCHEMA_DRIFT:
            mutated = dict(payload)
            if policy.target_field and policy.target_field in mutated:
                mutated.pop(policy.target_field)
            mutated["_contract_violation"] = f"missing required field '{policy.target_field}'"
            return mutated

        if policy.mode == ChaosMode.ARTIFICIAL_LATENCY:
            rng = policy.rng()
            jitter = rng.randint(0, policy.jitter_ms) if policy.jitter_ms else 0
            time.sleep((policy.delay_ms + jitter) / 1000.0)
            return payload

        if policy.mode == ChaosMode.TRUNCATED_RESPONSE:
            body = json.dumps(payload, separators=(",", ":"))
            truncated = body[: policy.truncate_at]
            return {"__raw__": truncated, "_contract_violation": "truncated JSON payload"}

        if policy.mode == ChaosMode.FALSE_SUCCESS:
            mutated = dict(payload)
            mutated["success"] = True
            mutated["_contract_violation"] = "reported success but state was not applied"
            return mutated

        if policy.mode == ChaosMode.DECOY_ERROR:
            mutated = dict(payload)
            mutated["success"] = False
            mutated["error"] = "INSUFFICIENT_FUNDS: balance below requested amount"
            mutated["_contract_violation"] = "operation declined by upstream"
            return mutated

        if policy.mode == ChaosMode.TIMEOUT_CASCADE:
            dep = policy.depends_on or "unknown"
            mutated = dict(payload)
            mutated["success"] = False
            mutated["error"] = f"UPSTREAM_TIMEOUT: dependency '{dep}' did not respond"
            mutated["_contract_violation"] = "dependency failure"
            return mutated

        return payload

    def active_modes(self, scenario_id: str) -> List[str]:
        policy = self.by_id.get(scenario_id)
        if not policy:
            return []
        return [policy.mode.value]
