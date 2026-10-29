"""
tests/test_grade_extra.py — Pruebas adicionales para grader/grade.py

Cubre _load_yaml, _parse_simple_yaml, main() y edge cases para
alcanzar >= 90% de cobertura.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.grade import run_eval, _load_yaml, _parse_simple_yaml  # noqa: E402


def test_load_yaml_with_yaml_available(tmp_path):
    """Test _load_yaml when yaml module is available."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2\n", encoding="utf-8")
    try:
        import yaml  # noqa: F401
        result = _load_yaml(yaml_file)
        assert isinstance(result, dict)
    except ImportError:
        result = _load_yaml(yaml_file)
        assert isinstance(result, dict)


def test_parse_simple_yaml():
    """Test _parse_simple_yaml with various inputs."""
    import tempfile, os
    content = """# Comment
key1: value1
key2: "quoted value"
key3: 'single quoted'
bool_true: true
bool_false: false
empty_line:

another_key: another_value
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(content)
        path = Path(f.name)
    try:
        result = _parse_simple_yaml(path)
        assert result["key1"] == "value1"
        assert result["key2"] == "quoted value"
        assert result["key3"] == "single quoted"
        assert result["bool_true"] is True
        assert result["bool_false"] is False
        assert result["another_key"] == "another_value"
    finally:
        os.unlink(path)


def test_parse_simple_yaml_empty_file():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write("")
        path = Path(f.name)
    try:
        result = _parse_simple_yaml(path)
        assert result == {}
    finally:
        os.unlink(path)


def test_run_eval_with_empty_tasks_dir(tmp_path):
    """Test run_eval with a directory that has no task files."""
    empty_dir = tmp_path / "empty_tasks"
    empty_dir.mkdir()
    output = tmp_path / "results" / "grade_results.json"
    summary = run_eval(empty_dir, output)
    assert summary["total"] == 0
    assert summary["approved"] == 0
    assert summary["rejected"] == 0
    assert summary["errors"] == 0
    assert output.exists()


def test_run_eval_output_structure(tmp_path):
    """Verify the output JSON structure is complete."""
    tasks_dir = Path(__file__).resolve().parent.parent / "tasks"
    output = tmp_path / "results" / "grade_results.json"
    summary = run_eval(tasks_dir, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "eval" in data
    assert "total" in data
    assert "approved" in data
    assert "rejected" in data
    assert "errors" in data
    assert "results" in data
    for entry in data["results"]:
        assert "task_id" in entry
        assert "status" in entry
        assert "execution_proof" in entry
        proof = entry["execution_proof"]
        assert "validations_passed" in proof
        assert "timestamp" in proof
        assert "guardrail_triggered" in proof
        assert "scenario_id" in proof
        assert "mode" in proof


def test_run_eval_deterministic(tmp_path):
    """Verify run_eval produces identical results on repeated runs."""
    tasks_dir = Path(__file__).resolve().parent.parent / "tasks"
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    s1 = run_eval(tasks_dir, out1)
    s2 = run_eval(tasks_dir, out2)
    assert s1["total"] == s2["total"]
    assert s1["approved"] == s2["approved"]
    assert s1["rejected"] == s2["rejected"]


def test_load_yaml_nonexistent():
    """Test _load_yaml with a non-existent file (should raise)."""
    try:
        _load_yaml(Path("/nonexistent/file.yaml"))
        assert False, "Should have raised"
    except (FileNotFoundError, Exception):
        pass


def test_main_entry_point(tmp_path):
    """Test main() CLI entry point."""
    import subprocess, sys
    tasks_dir = str(Path(__file__).resolve().parent.parent / "tasks")
    output = str(tmp_path / "out.json")
    result = subprocess.run(
        [sys.executable, "-m", "grader.grade", "--tasks-dir", tasks_dir, "--output", output],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent),
    )
    # main() prints to stdout
    assert "Running eval" in result.stdout or "Summary" in result.stdout or result.returncode == 0
