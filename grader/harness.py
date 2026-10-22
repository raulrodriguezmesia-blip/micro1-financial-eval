"""
grader/harness.py — Cliente MCP y harness de agente para el eval micro1.

Proporciona MCPClient (JSON-RPC 2.0 sobre stdio) y AgentHarness, que ejecuta un
agente contra el servidor MCP y devuelve las respuestas para validación.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional


class MCPClient:
    def __init__(self, server_command: List[str]) -> None:
        self.server_command = server_command
        self._proc: Optional[subprocess.Popen] = None
        self._id = 0

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def call(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._proc:
            raise RuntimeError("MCPClient not started")
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        assert self._proc.stdin
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        return json.loads(line)


class AgentHarness:
    """Ejecuta un agente de referencia contra el servidor MCP."""

    def __init__(self, client: MCPClient) -> None:
        self.client = client
        self.seen_ids: List[str] = []

    def run_tool(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.call(tool, arguments)
        if isinstance(result, dict) and result.get("result"):
            inner = result["result"]
            if isinstance(inner, str):
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    return {"__raw__": inner, "_contract_violation": "non-JSON text response"}
            return inner
        return result
