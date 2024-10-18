# Copyright 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft
"""Unit tests for linters."""

import pathlib
import subprocess
import sys

import pytest

from charmcraft import linters
from charmcraft.models.lint import LintResult


@pytest.fixture
def valid_venv_path(fake_path) -> pathlib.Path:
    """Create and return a fakefs path that contains a valid venv structure"""
    (fake_path / "venv" / "lib").mkdir(parents=True)
    return fake_path


def test_pip_check_not_venv(fake_path: pathlib.Path):
    lint = linters.PipCheck()
    assert lint.run(fake_path) == LintResult.NONAPPLICABLE
    assert lint.text == "Charm does not contain a Python venv."


def test_pip_invalid_venv(fake_path: pathlib.Path):
    (fake_path / "venv").mkdir()
    lint = linters.PipCheck()
    assert lint.run(fake_path) == LintResult.NONAPPLICABLE
    assert lint.text == "Python venv is not valid."


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_success(valid_venv_path: pathlib.Path, fp):
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Loo loo loo, doing pip stuff. Pip stuff is my favourite stuff.",
    )

    lint = linters.PipCheck()
    assert lint.run(valid_venv_path) == LintResult.OK
    assert lint.text == linters.PipCheck.text


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_warning(valid_venv_path: pathlib.Path, fp):
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=1,
        stdout="This error was sponsored by Raytheon Knife Missiles™",
    )

    lint = linters.PipCheck()
    assert lint.run(valid_venv_path) == LintResult.WARNING
    assert lint.text == "This error was sponsored by Raytheon Knife Missiles™"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_exception(valid_venv_path: pathlib.Path, monkeypatch):
    def _raises_eperm(*args, **kwargs) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(subprocess, "run", _raises_eperm)

    lint = linters.PipCheck()
    assert lint.run(valid_venv_path) == LintResult.NONAPPLICABLE
    assert (
        lint.text
        == f"Permission denied: Could not run Python executable at {sys.executable}."
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_repair_no_bin(valid_venv_path: pathlib.Path, fp):
    """Check that the bin directory is deleted if it was missing before"""
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Gosh, I sure hope I remember where everything went.",
    )
    lint = linters.PipCheck()

    # Make sure it doesn't leave behind "bin" if it didn't exist
    assert lint.run(valid_venv_path) == LintResult.OK
    assert lint.text == "Virtual environment is valid."
    assert not (valid_venv_path / "venv" / "bin").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_repair_no_py(valid_venv_path: pathlib.Path, fp):
    """Check that the python symlink is deleted if it was missing before"""
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Gosh, I sure hope I remember where everything went.",
    )
    lint = linters.PipCheck()

    # Make sure it keeps "bin" if only the Python binary didn't exist
    (valid_venv_path / "venv" / "bin").mkdir()
    assert lint.run(valid_venv_path) == LintResult.OK
    assert lint.text == "Virtual environment is valid."
    assert (valid_venv_path / "venv" / "bin").exists()
    assert not (valid_venv_path / "venv" / "bin" / "python").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported.")
def test_pip_check_repair_all(valid_venv_path: pathlib.Path, fp):
    """Check that nothing is changed if all components are present"""
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Gosh, I sure hope I remember where everything went.",
    )
    lint = linters.PipCheck()

    (valid_venv_path / "venv" / "bin").mkdir()
    (valid_venv_path / "venv" / "bin" / "python").touch()

    assert lint.run(valid_venv_path) == LintResult.OK
    assert lint.text == "Virtual environment is valid."
    assert (valid_venv_path / "venv" / "bin" / "python").is_file()
