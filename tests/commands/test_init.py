# Copyright 2020-2022 Canonical Ltd.
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

import datetime
import io
import os
import re
import subprocess
import sys
from argparse import Namespace
from unittest.mock import patch

import pydocstyle
import pytest
from craft_cli import CraftError
from flake8.api.legacy import get_style_guide

from charmcraft.commands.init import DEFAULT_PROFILE, PROFILES, InitCommand
from charmcraft.models.charmcraft import Project
from charmcraft.utils import S_IXALL
from tests.test_infra import get_python_filepaths


def pep8_test(python_filepaths):
    """Helper to check PEP8 (used from this module and from test_init.py to check templates)."""
    style_guide = get_style_guide()
    fake_stdout = io.TextIOWrapper(io.BytesIO())
    with patch("sys.stdout", fake_stdout):
        report = style_guide.check_files(python_filepaths)

    # if flake8 didn't report anything, we're done
    if report.total_errors == 0:
        return

    # grab on which files we have issues
    fake_stdout.seek(0)
    flake8_issues = fake_stdout.read().split("\n")

    if flake8_issues:
        msg = "Please fix the following flake8 issues!\n" + "\n".join(flake8_issues)
        pytest.fail(msg, pytrace=False)


def pep257_test(python_filepaths):
    """Helper to check PEP257 (used from this module and from test_init.py to check templates)."""
    to_ignore = {
        "D105",  # Missing docstring in magic method
        "D107",  # Missing docstring in __init__
    }
    to_include = pydocstyle.violations.conventions.pep257 - to_ignore
    errors = list(pydocstyle.check(python_filepaths, select=to_include))

    if errors:
        report = [f"Please fix files as suggested by pydocstyle ({len(errors):d} issues):"]
        report.extend(str(e) for e in errors)
        msg = "\n".join(report)
        pytest.fail(msg, pytrace=False)


def create_namespace(*, name="my-charm", author="J Doe", force=False, profile=DEFAULT_PROFILE):
    """Helper to create a valid namespace."""
    return Namespace(name=name, author=author, force=force, profile=profile)


@pytest.mark.parametrize("profile", list(PROFILES))
def test_init_pep257(tmp_path, config, profile):
    cmd = InitCommand(config)
    cmd.run(create_namespace(profile=profile))
    paths = get_python_filepaths(roots=[str(tmp_path / "src")], python_paths=[])
    pep257_test(paths)


@pytest.mark.parametrize("profile", list(PROFILES))
def test_init_pep8(tmp_path, config, *, author="J Doe", profile):
    cmd = InitCommand(config)
    cmd.run(create_namespace(author=author, profile=profile))
    paths = get_python_filepaths(
        roots=[str(tmp_path / "src"), str(tmp_path / "tests")], python_paths=[]
    )
    pep8_test(paths)


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
@pytest.mark.skipif(os.getenv("RUNNING_TOX"), reason="does not work inside tox")
@pytest.mark.parametrize("profile", list(PROFILES))
def test_tests(tmp_path, config, profile):
    # fix the PYTHONPATH and PATH so the tests in the initted environment use our own
    # virtualenv libs and bins (if any), as they need them, but we're not creating a
    # venv for the local tests (note that for CI doesn't use a venv)
    env = os.environ.copy()
    env_paths = [p for p in sys.path if "env/lib/python" in p]
    if env_paths:
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] += ":" + ":".join(env_paths)
        else:
            env["PYTHONPATH"] = ":".join(env_paths)
        for path in env_paths:
            bin_path = path[: path.index("env/lib/python")] + "env/bin"
            env["PATH"] = bin_path + ":" + env["PATH"]

    cmd = InitCommand(config)
    cmd.run(create_namespace(profile=profile))

    subprocess.run(["tox", "-v"], cwd=str(tmp_path), check=True, env=env)
