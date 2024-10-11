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
import sys

from charmcraft import linters
from charmcraft.models.lint import LintResult


def test_pip_check_not_venv(fake_path: pathlib.Path):
    lint = linters.PipCheck()
    assert lint.run(fake_path) == LintResult.NONAPPLICABLE
    assert lint.text == "Charm does not contain a Python venv."


def test_pip_check_success(fake_path: pathlib.Path, fp):
    (fake_path / "venv").mkdir()
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Loo loo loo, doing pip stuff. Pip stuff is my favourite stuff."
    )

    lint = linters.PipCheck()
    assert lint.run(fake_path) == LintResult.OK
    assert lint.text == linters.PipCheck.text


def test_pip_check_warning(fake_path: pathlib.Path, fp):
    (fake_path / "venv").mkdir()
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=1,
        stdout="This error was sponsored by Raytheon Knife Missiles™"
    )

    lint = linters.PipCheck()
    assert lint.run(fake_path) == LintResult.WARNING
    assert lint.text == "This error was sponsored by Raytheon Knife Missiles™"
