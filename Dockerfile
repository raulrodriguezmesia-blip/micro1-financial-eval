# =============================================================================
# Dockerfile — micro1-financial-eval
# Entorno aislado y reproducible para el servidor MCP adversario, el arnés
# de evaluación y la suite de pytest con cobertura de código.
# =============================================================================
FROM python:3.11-slim AS base

# Evita archivos .pyc y buffering de stdout/stderr en contenedores
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# =============================================================================
# Stage: dependencias
# =============================================================================
FROM base AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# =============================================================================
# Stage: runtime
# =============================================================================
FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY mcp_server/ ./mcp_server/
COPY grader/ ./grader/
COPY tasks/ ./tasks/
COPY agents/ ./agents/
COPY run_eval.sh ./
COPY README.md ./
COPY requirements.txt ./

# Usuario no-root para ejecución segura en contenedor
RUN useradd -m -s /bin/bash evaluser && chown -R evaluser:evaluser /app
USER evaluser

# Puerto opcional si se expone el servidor MCP vía HTTP en el futuro
EXPOSE 8000

# Comando por defecto: ejecutar la suite de evaluación con cobertura
CMD ["python", "-m", "grader.grade", "--tasks-dir", "tasks", "--output", "results/grade_results.json"]
