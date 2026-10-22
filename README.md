# micro1-financial-eval

Eval micro1 para el micro1 Eval Hackathon. Demuestra guardrails de "Zero Hallucination"
sobre un servidor MCP financiero adversario y un grader determinista O(1) que emite
`executionProof` por tarea.

## Estructura

- `mcp_server/` — Servidor MCP FastMCP con herramientas financieras y motor de caos
  (`chaos.py`) que inyecta fallos deterministas (schema drift, latencia, respuesta
  truncada, éxito falso, error engañoso, cascada de timeout).
- `grader/` — Validador O(1) (`invariants.py`), cliente MCP (`harness.py`) y
  orquestador de evaluación (`grade.py`).
- `tasks/task_01.yaml` … `task_10.yaml` — Definición de las 10 tareas del eval.
- `agents/reference_agent.py` — Agente de referencia que llama al MCP adversario.
- `run_eval.sh` — Script de ejecución end-to-end.

## Ejecución

```bash
./run_eval.sh
```

El reporte se escribe en `results/grade_results.json` con el `executionProof` de cada
tarea (`validations_passed`, `guardrail_triggered`, `scenario_id`, `mode`).