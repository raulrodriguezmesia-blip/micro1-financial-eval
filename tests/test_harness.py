"""
tests/test_harness.py — Pruebas unitarias para grader/harness.py

Valida MCPClient (JSON-RPC 2.0 sobre stdio) y AgentHarness sin servidor MCP vivo.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.harness import MCPClient, AgentHarness  # noqa: E402


def test_mcpclient_init():
    client = MCPClient(["python", "server.py"])
    assert client.server_command == ["python", "server.py"]
    assert client._proc is None
    assert client._id == 0


def test_mcpclient_next_id_increments():
    client = MCPClient(["python", "server.py"])
    assert client._next_id() == 1
    assert client._next_id() == 2
    assert client._next_id() == 3


def test_mcpclient_call_without_start_raises():
    client = MCPClient(["python", "server.py"])
    try:
        client.call("test_tool", {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not started" in str(e)


def test_mcpclient_start_and_stop():
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()
    with patch("subprocess.Popen", return_value=mock_proc):
        client = MCPClient(["python", "server.py"])
        client.start()
        assert client._proc is mock_proc
        client.stop()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)
        assert client._proc is None


def test_mcpclient_stop_timeout_kills():
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)
    with patch("subprocess.Popen", return_value=mock_proc):
        client = MCPClient(["python", "server.py"])
        client.start()
        client.stop()
        mock_proc.kill.assert_called_once()
        assert client._proc is None


def test_mcpclient_stop_when_not_started():
    client = MCPClient(["python", "server.py"])
    client.stop()  # Should not raise
    assert client._proc is None


def test_mcpclient_call_success():
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.readline.return_value = '{"jsonrpc":"2.0","id":1,"result":{"status":"ok"}}\n'
    mock_proc.stderr = MagicMock()
    with patch("subprocess.Popen", return_value=mock_proc):
        client = MCPClient(["python", "server.py"])
        client.start()
        result = client.call("test_tool", {"arg": "value"})
        assert result == {"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}
        mock_proc.stdin.write.assert_called_once()
        mock_proc.stdin.flush.assert_called_once()


def test_agentharness_init():
    client = MCPClient(["python", "server.py"])
    harness = AgentHarness(client)
    assert harness.client is client
    assert harness.seen_ids == []


def test_agentharness_run_tool_with_dict_result():
    mock_client = MagicMock()
    mock_client.call.return_value = {"result": {"success": True, "balance": 5000.0}}
    harness = AgentHarness(mock_client)
    result = harness.run_tool("get_balance", {"accountId": "ACC_001"})
    assert result == {"success": True, "balance": 5000.0}
    mock_client.call.assert_called_once_with("get_balance", {"accountId": "ACC_001"})


def test_agentharness_run_tool_with_string_json_result():
    mock_client = MagicMock()
    mock_client.call.return_value = {"result": '{"success": true, "balance": 5000.0}'}
    harness = AgentHarness(mock_client)
    result = harness.run_tool("get_balance", {"accountId": "ACC_001"})
    assert result == {"success": True, "balance": 5000.0}


def test_agentharness_run_tool_with_invalid_json_string():
    mock_client = MagicMock()
    mock_client.call.return_value = {"result": "not valid json"}
    harness = AgentHarness(mock_client)
    result = harness.run_tool("get_balance", {"accountId": "ACC_001"})
    assert result == {"__raw__": "not valid json", "_contract_violation": "non-JSON text response"}


def test_agentharness_run_tool_no_result():
    mock_client = MagicMock()
    mock_client.call.return_value = {"error": "something went wrong"}
    harness = AgentHarness(mock_client)
    result = harness.run_tool("get_balance", {"accountId": "ACC_001"})
    assert result == {"error": "something went wrong"}


def test_agentharness_run_tool_non_dict_result():
    mock_client = MagicMock()
    mock_client.call.return_value = "raw string"
    harness = AgentHarness(mock_client)
    result = harness.run_tool("get_balance", {"accountId": "ACC_001"})
    assert result == "raw string"
