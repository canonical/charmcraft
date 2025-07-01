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


@pytest.mark.slow
@pytest.mark.parametrize(
    "pip_cmd",
    [
        ["--version"],
        ["install", "pytest", "hypothesis"],
    ],
)
def test_pip_check_success(tmp_path: pathlib.Path, pip_cmd: list[str]):
    venv_path = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    subprocess.run([venv_path / "bin" / "python", "-m", "pip", *pip_cmd], check=True)

    lint = linters.PipCheck()
    assert lint.run(tmp_path) == LintResult.OK
    assert lint.text == linters.PipCheck.text


@pytest.mark.slow
@pytest.mark.parametrize(
    "pip_cmd",
    [
        ["install", "--no-deps", "pydantic==2.9.2"],
    ],
)
def test_pip_check_failure(tmp_path: pathlib.Path, pip_cmd: list[str]):
    venv_path = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    subprocess.run([venv_path / "bin" / "python", "-m", "pip", *pip_cmd], check=True)

    lint = linters.PipCheck()
    assert lint.run(tmp_path) == LintResult.WARNING
    assert "pydantic 2.9.2 requires pydantic-core" in lint.text
