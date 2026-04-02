"""
Helpers for bootstrapping Zabbix wrapper scripts with a local virtualenv.
"""

import os
import sys
from pathlib import Path


def find_venv_python(project_dir: Path) -> Path | None:
    """Return the local venv Python path when present."""
    python_path = project_dir / "fiberhome" / ".venv" / "bin" / "python"
    if python_path.exists():
        return python_path
    return None


def reexec_with_venv(project_dir: Path, current_executable: str | None = None) -> None:
    """Re-exec the current process with the local venv Python if available."""
    venv_python = find_venv_python(project_dir)
    if venv_python is None:
        return

    current = Path(current_executable or sys.executable).resolve()
    target = venv_python.resolve()
    if current == target:
        return

    os.execv(os.fspath(target), [os.fspath(target), *sys.argv])
