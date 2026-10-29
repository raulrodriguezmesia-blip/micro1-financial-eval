import sys
from pathlib import Path
from unittest.mock import patch

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.grade import main, _now_iso, _load_yaml, _TASK_PAYLOADS, _REQUIRED_FIELDS, _TOOL_NAME  # noqa: E402


def test_now_iso():
    ts = _now_iso()
    assert "T" in ts
    assert "+" in ts or "Z" in ts


def test_load_yaml_simple(tmp_path):
    content = "scenario_id: S1\nchaos_mode: NONE\n"
    f = tmp_path / "task_test.yaml"
    f.write_text(content, encoding="utf-8")
    result = _load_yaml(f)
    assert result.get("scenario_id") == "S1"
    assert result.get("chaos_mode") == "NONE"


def test_load_yaml_with_yaml_module(tmp_path):
    content = "key: value\nnested:\n  sub: data\n"
    f = tmp_path / "task_yaml.yaml"
    f.write_text(content, encoding="utf-8")
    result = _load_yaml(f)
    assert isinstance(result, dict)


def test_main_direct(tmp_path, monkeypatch):
    tasks_dir = str(Path(__file__).resolve().parent.parent / "tasks")
    output = str(tmp_path / "out.json")
    monkeypatch.setattr("sys.argv", ["grade", "--tasks-dir", tasks_dir, "--output", output])
    main()
    import json
    data = json.loads(Path(output).read_text(encoding="utf-8"))
    assert data["total"] == 10


def test_task_payloads_structure():
    assert len(_TASK_PAYLOADS) == 10
    for tid, payload in _TASK_PAYLOADS.items():
        assert isinstance(payload, dict)


def test_required_fields_structure():
    assert len(_REQUIRED_FIELDS) == 10
    for tid, fields in _REQUIRED_FIELDS.items():
        assert isinstance(fields, list)


def test_tool_name_structure():
    assert len(_TOOL_NAME) == 10
    for tid, tool in _TOOL_NAME.items():
        assert isinstance(tool, str)
