# 🛡️ micro1-financial-eval: Adversarial MCP Evaluation Suite

[![CI/CD Pipeline](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/raulrodriguezmesia-blip/micro1-financial-eval/actions)
[![Coverage Gate](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen.svg)]()
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/protocol-MCP_FastMCP-green.svg)](https://modelcontextprotocol.io)
[![Guardrails](https://img.shields.io/badge/guardrails-O%281%29_Invariants-orange.svg)]()
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

An end-to-end, deterministic evaluation benchmark designed for the **micro1 Eval Hackathon**. This suite tests AI agents against an **Adversarial Model Context Protocol (MCP) server** equipped with a chaotic mutation engine, validated by an $O(1)$ Zero-Hallucination guardrail layer that emits cryptographic-like `ExecutionProof` metadata for auditability.

---

## 📐 Architecture Overview

The system establishes a strict separation of concerns: reasoning occurs within the model loop, but **verdict and validation correctness sit entirely outside the model's influence**.

```
┌─────────────────┐       JSON-RPC 2.0 / stdio        ┌─────────────────────────┐
│                 │ ────────────────────────────────> │                         │
│  Agent Harness  │                                   │   Adversarial MCP       │
│  (Orchestrator) │ <──────────────────────────────── │   Server (FastMCP)      │
└────────┬────────┘      Adversarial Tool Payload     └────────────┬────────────┘
│                                                         │
│ Intercepts Response                                     │ Injects Chaos
▼                                                         ▼
┌──────────────────────────────────┐                      ┌──────────────────┐
│   Zero-Hallucination Guardrails  │                      │   Chaos Engine   │
│   - O(1) Invariants Check        │                      │   - Drift / Delay│
│   - ExecutionProof Generation    │                      │   - Truncations  │
└────────────────┬─────────────────┘                      └──────────────────┘
│
▼
┌────────────────────────┐
│  grade_results.json    │
│  (Traceable Audit Log) │
└────────────────────────┘
```

---

## ✨ Key Features

1. **Adversarial FastMCP Server (`mcp_server/`)**: Simulates realistic upstream microservice failures, corruption, and network disruptions without breaking protocol specs.
2. **Deterministic $O(1)$ Invariants (`grader/invariants.py`)**: Ported from enterprise treasury systems (**FinGuard Core**). Includes UUID checks, transaction limit enforcement, solvency verification, and dependency ordering.
3. **ExecutionProof Auditability**: Every evaluated task produces an immutable validation payload containing timestamp, rule pass/fail vectors, and explicit trigger reasons.
4. **Zero-Trust Agent Harness (`grader/harness.py`)**: Intercepts tool calls over `stdio` via JSON-RPC 2.0 to catch non-deterministic hallucinations before state mutation.
5. **Production CI/CD & Quality Gate**: Automated GitHub Actions testing workflow enforcing a $\ge 90\%$ code coverage threshold with `pytest-cov`.
6. **Multi-Stage Containerization**: Hardened non-root `Dockerfile` and `docker-compose.yml` for isolated and 100% reproducible execution.

---

## ⚡ Chaos Mutation Engine Modes

The `ChaosEngine` (`mcp_server/chaos.py`) injects 6 deterministic failure modes into financial payloads:

| Mode | Target / Impact | Guardrail Defense |
| :--- | :--- | :--- |
| **`SCHEMA_DRIFT`** | Mutates field types/names (e.g., `amount` string injection) | `PARSE_INTEGRITY` |
| **`ARTIFICIAL_LATENCY`** | Delays response by custom thresholds ($> 2000\text{ms}$) | `TIMEOUT_CASCADE` |
| **`TRUNCATED_RESPONSE`** | Cuts off required JSON balance payload keys | `CONTRACT_COMPLETENESS` |
| **`FALSE_SUCCESS`** | Returns `SUCCESS` flag with corrupted `TX_ID` or unverified state | `STATE_VERIFICATION` |
| **`DECOY_ERROR`** | Emits fake 500 exceptions to trick retry loops | `BOUNDED_RETRY` |
| **`TIMEOUT_CASCADE`** | Simulates upstream gateway timeouts (504) | `NO_UNSAFE_RETRY` |

---

## 🧪 Test Suite & Coverage

The repository includes a 19-test suite covering invariant verification, chaos mutations, and orchestration:

```bash
# Run unit & integration tests with coverage report
pytest --cov=grader --cov=mcp_server --cov-fail-under=90
```

🐳 **Docker Execution**

To run the suite inside a fully isolated, non-root container environment:

```bash
# Build and run using Docker Compose
docker-compose up --build
```

⚙️ **CI/CD Pipeline** (`.github/workflows/eval-ci.yml`)

On every push or pull request touching the evaluation suite:

- Provisions Python 3.10 with cached dependencies
- Runs pytest and enforces the $\ge 90\%$ coverage quality gate
- Executes the full benchmark suite (`grade.py`)
- Uploads coverage report artifacts (`htmlcov/`) and evaluation proofs (`grade_results.json`)

---

## 🗂️ Evaluation Tasks Matrix (`tasks/`)

The suite features 10 comprehensive evaluation scenarios:

* 📄 **`task_01` – `task_03`**: Solvency & Boundary checks ($50,000 limit enforcement, FX balance checks).
* 📄 **`task_04` – `task_06`**: Schema integrity & Idempotency verification under network retries.
* 📄 **`task_07` – `task_10`**: Cascading failure resilience, decoy error rejection, and state rollback checks.

---

## 🚀 Quick Start (Local)

### Installation

```bash
# Clone the repository
git clone https://github.com/raulrodriguezmesia-blip/micro1-financial-eval.git
cd micro1-financial-eval

# Create virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running the End-to-End Benchmark

```bash
chmod +x run_eval.sh
./run_eval.sh
```

---

## 📊 Sample ExecutionProof Output

When the evaluation finishes, an audit log is exported to `results/grade_results.json`:

```json
{
  "task_id": "task_02",
  "status": "REJECTED",
  "execution_proof": {
    "timestamp": "2026-10-21T22:15:00.123Z",
    "scenario_id": "SCENARIO_FALSE_SUCCESS",
    "chaos_mode": "FALSE_SUCCESS",
    "validations_passed": [
      "UUID_CHECK",
      "IDEMPOTENCY_CHECK",
      "CONTRACT_COMPLETENESS"
    ],
    "guardrail_triggered": true,
    "failure_reason": "State verification failed: Response reported success but transaction ID was corrupted."
  }
}
```

---

## 🛠️ Project Structure

```
micro1-financial-eval/
├── .github/workflows/
│   └── eval-ci.yml           # GitHub Actions CI/CD workflow
├── agents/
│   └── reference_agent.py    # Reference agent interacting with adversarial MCP
├── grader/
│   ├── grade.py              # Main evaluation orchestrator & runner
│   ├── harness.py            # MCP stdio Client & Agent Harness
│   └── invariants.py         # O(1) Zero-Hallucination rules & ExecutionProof
├── mcp_server/
│   ├── chaos.py              # ChaosEngine with 6 mutation algorithms
│   ├── scenarios.json        # Scenario definitions & chaos configs
│   └── server.py             # FastMCP financial tool server
├── tasks/                    # Task definitions (task_01.yaml -> task_10.yaml)
├── tests/                    # Unit and integration tests (19 passed)
├── .gitignore
├── Dockerfile                # Multi-stage non-root container configuration
├── docker-compose.yml        # Multi-service network composition
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies (includes pytest-cov)
└── run_eval.sh               # Execution entry point
```

---

## 👤 Author

**Raúl Rodríguez Mesia**
Computer Science Engineer | Senior AI Prompt Consultant & MCP Architect
Tumbes, Peru
GitHub: @raulrodriguezmesia-blip
