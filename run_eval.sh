#!/usr/bin/env bash
set -euo pipefail

# Ejecuta el eval micro1 end-to-end: genera tareas, inyecta caos, valida invariantes
# y escribe results/grade_results.json con executionProof por tarea.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python -m grader.grade --tasks-dir tasks --output results/grade_results.json

echo "Reporte escrito en results/grade_results.json"