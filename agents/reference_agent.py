"""
agents/reference_agent.py — Agente de referencia para el eval micro1.

Simula un agente que llama al servidor MCP adversario y, de forma ingenua, confía
en la respuesta recibida sin aplicar guardrails propios. Se usa para demostrar que
el grader (invariantes O(1) + executionProof) detecta las alucinaciones/fallos del
canal MCP.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from grader.harness import AgentHarness, MCPClient


class ReferenceAgent:
    def __init__(self, server_command: list[str]) -> None:
        self.client = MCPClient(server_command)
        self.harness = AgentHarness(self.client)

    def run(self) -> None:
        self.client.start()
        try:
            # Ejemplo: consulta de saldo
            resp = self.harness.run_tool("get_balance", {"accountId": "ACC_USD_001"})
            print(json.dumps(resp, ensure_ascii=False))
        finally:
            self.client.stop()


if __name__ == "__main__":
    ReferenceAgent(["python", "mcp_server/server.py"]).run()
