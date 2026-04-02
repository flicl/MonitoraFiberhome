import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fiberhome.bootstrap import find_venv_python, reexec_with_venv


class WrapperUtilsTests(unittest.TestCase):
    def test_find_venv_python_returns_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            python_path = project_dir / "fiberhome" / ".venv" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.write_text("", encoding="utf-8")

            resolved = find_venv_python(project_dir)

            self.assertEqual(resolved, python_path)

    def test_find_venv_python_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolved = find_venv_python(Path(temp_dir))

            self.assertIsNone(resolved)

    def test_reexec_with_venv_executes_target_python(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            python_path = project_dir / "fiberhome" / ".venv" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.write_text("", encoding="utf-8")

            with patch("os.execv") as execv_mock:
                reexec_with_venv(project_dir, current_executable="/usr/bin/python3")

            execv_mock.assert_called_once_with(
                os.fspath(python_path),
                [os.fspath(python_path), *sys.argv],
            )

    def test_reexec_with_venv_skips_when_already_using_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            python_path = project_dir / "fiberhome" / ".venv" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.write_text("", encoding="utf-8")

            with patch("os.execv") as execv_mock:
                reexec_with_venv(project_dir, current_executable=os.fspath(python_path))

            execv_mock.assert_not_called()
