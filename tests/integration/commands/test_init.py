# Copyright 2023 Canonical Ltd.
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
"""Unit tests for init command."""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
from typing import Set

import pytest

import charmcraft
from charmcraft.application import commands


BASIC_INIT_FILES = frozenset(
    pathlib.Path(p)
    for p in (
        ".gitignore",
        "charmcraft.yaml",
        "CONTRIBUTING.md",
        "LICENSE",
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        "src",
        "src/charm.py",
        "tests",
        "tests/integration",
        "tests/integration/test_charm.py",
        "tests/unit",
        "tests/unit/test_charm.py",
        "tox.ini",
    )
)


@pytest.fixture()
def init_command():
    return commands.InitCommand({"app": charmcraft.application.APP_METADATA, "services": None})


def create_namespace(
    *, name="my-charm", author="J Doe", force=False, profile=commands.init.DEFAULT_PROFILE
):
    """Helper to create a valid namespace."""
    return argparse.Namespace(name=name, author=author, force=force, profile=profile)


@pytest.mark.parametrize(
    ("profile", "expected_files"),
    [
        ("simple", BASIC_INIT_FILES),
        ("machine", BASIC_INIT_FILES),
        ("kubernetes", BASIC_INIT_FILES),
    ],
)
def test_files_created_correct(
    new_path, init_command, profile: str, expected_files: Set[pathlib.Path]
):
    init_command.run(create_namespace(profile=profile))

    actual_files = {p.relative_to(new_path) for p in new_path.rglob("*")}

    assert actual_files == expected_files
    assert re.search(r"^name: my-charm$", (new_path / "charmcraft.yaml").read_text(), re.MULTILINE)


def test_force(tmp_path, init_command):
    tmp_file = tmp_path / "README.md"
    with tmp_file.open("w") as f:
        f.write("This is a nonsense readme")

    init_command.run(create_namespace(force=True))

    # Check that init ran
    assert (tmp_path / "LICENSE").exists()

    # Check that init did not overwrite files
    with tmp_file.open("r") as f:
        assert f.read() == "This is a nonsense readme"
