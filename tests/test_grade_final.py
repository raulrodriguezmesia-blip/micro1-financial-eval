import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

for _base in ("..", "."):
    _candidate = str(Path(__file__).resolve().parent / _base)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from grader.grade import _load_yaml  # noqa: E402


def test_load_yaml_without_yaml_module(tmp_path):
    """Cover the except ImportError branch in _load_yaml."""
    content = "key: value\n"
    f = tmp_path / "test.yaml"
    f.write_text(content, encoding="utf-8")
    # Mock yaml as unavailable
    with patch.dict("sys.modules", {"yaml": None}):
        result = _load_yaml(f)
        assert isinstance(result, dict)


def test_main_as_script(tmp_path):
    """Cover the if __name__ == '__main__' block."""
    import runpy
    tasks_dir = str(Path(__file__).resolve().parent.parent / "tasks")
    output = str(tmp_path / "out.json")
    import sys as _sys
    _sys.argv = ["grade", "--tasks-dir", tasks_dir, "--output", output]
    runpy.run_path("grader/grade.py", run_name="__main__")
    import json
    data = json.loads(Path(output).read_text(encoding="utf-8"))
    assert data["total"] == 10
