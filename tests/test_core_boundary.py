"""The core stays plain Python: the screens and the agent's tools call it, and it never imports Streamlit."""

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "login_investigator"


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_no_core_module_imports_streamlit():
    files = sorted(CORE.glob("*.py"))
    assert files
    offenders = [
        f.name for f in files if any(m.split(".")[0] == "streamlit" for m in imported_modules(f))
    ]
    assert offenders == []
