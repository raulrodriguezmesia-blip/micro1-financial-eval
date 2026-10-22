"""
tests/test_invariants.py — Pruebas unitarias para grader/invariants.py

Valida cada invariante O(1) del Zero-Hallucination guardrail y la generación
correcta de ExecutionProof. Diseñado para ejecutarse sin servidor MCP vivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.invariants import ValidationResult, validate_task  # noqa: E402


def _valid_payload() -> dict:
    return {
        "success": True,
        "amount": 1000.0,
        "requestId": "550e8400-e29b-41d4-a716-446655440000",
        "newBalanceSrc": 4000.0,
        "balance": 5000.0,
    }


def test_uuid_check_passes_with_valid_uuid() -> None:
    result = validate_task(
        task_id="t1", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440000",
        amount=100.0, balance=5000.0, tool_name="transfer_funds",
    )
    assert result.status == "APPROVED"
    assert "UUID_CHECK" in result.execution_proof.validations_passed


def test_uuid_check_fails_with_invalid_uuid() -> None:
    result = validate_task(
        task_id="t2", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="not-a-uuid",
        amount=100.0, balance=5000.0, tool_name="transfer_funds",
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_tx_limit_check_passes_under_limit() -> None:
    result = validate_task(
        task_id="t3", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440001",
        amount=49999.99, balance=5000.0, tool_name="transfer_funds",
    )
    assert "TX_LIMIT_CHECK" in result.execution_proof.validations_passed


def test_tx_limit_check_triggers_guardrail_over_limit() -> None:
    result = validate_task(
        task_id="t4", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440002",
        amount=75000.0, balance=5000.0, tool_name="transfer_funds",
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_solvency_check_passes_for_fx_with_sufficient_balance() -> None:
    result = validate_task(
        task_id="t5", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440003",
        amount=1000.0, balance=5000.0, tool_name="convert_fx",
    )
    assert "SOLVENCY_CHECK" in result.execution_proof.validations_passed


def test_solvency_check_fails_for_fx_insufficient_balance() -> None:
    result = validate_task(
        task_id="t6", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440004",
        amount=8000.0, balance=3000.0, tool_name="convert_fx",
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_contract_completeness_passes_when_fields_present() -> None:
    result = validate_task(
        task_id="t7", scenario_id="NONE", chaos_mode="NONE",
        response={"from": "A", "to": "B", "amount": 100.0},
        request_id="550e8400-e29b-41d4-a716-446655440005",
        amount=100.0, balance=5000.0,
        required_fields=["from", "to", "amount"],
    )
    assert "CONTRACT_COMPLETENESS" in result.execution_proof.validations_passed


def test_contract_completeness_fails_when_fields_missing() -> None:
    result = validate_task(
        task_id="t8", scenario_id="NONE", chaos_mode="NONE",
        response={"from": "A"},
        request_id="550e8400-e29b-41d4-a716-446655440006",
        amount=100.0, balance=5000.0,
        required_fields=["from", "to", "amount"],
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_parse_integrity_fails_on_contract_violation() -> None:
    result = validate_task(
        task_id="t9", scenario_id="NONE", chaos_mode="TRUNCATED_RESPONSE",
        response={"_contract_violation": "truncated JSON payload"},
        request_id="550e8400-e29b-41d4-a716-446655440007",
        amount=100.0, balance=5000.0,
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_idempotency_check_fails_on_duplicate_request_id() -> None:
    result = validate_task(
        task_id="t10", scenario_id="NONE", chaos_mode="NONE", response={},
        request_id="550e8400-e29b-41d4-a716-446655440008",
        amount=100.0, balance=5000.0,
        idempotency_seen={"550e8400-e29b-41d4-a716-446655440008"},
    )
    assert result.status == "REJECTED"
    assert result.execution_proof.guardrail_triggered is True


def test_execution_proof_contains_required_fields() -> None:
    result = validate_task(
        task_id="t11", scenario_id="S1", chaos_mode="SCHEMA_DRIFT", response={},
        request_id="550e8400-e29b-41d4-a716-446655440009",
        amount=100.0, balance=5000.0,
    )
    proof = result.execution_proof
    assert proof.scenario_id == "S1"
    assert proof.mode == "SCHEMA_DRIFT"
    assert proof.timestamp != ""
    assert isinstance(proof.validations_passed, list)
    assert isinstance(proof.guardrail_triggered, bool)
