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
"""Tests for init command."""
import argparse
import contextlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
from unittest import mock

import pydocstyle
import pytest
import pytest_check

import charmcraft
from charmcraft import errors
from charmcraft.application import commands
from charmcraft.utils import S_IXALL

with contextlib.suppress(ImportError):
    import pwd

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
UNKNOWN_AUTHOR_REGEX = re.compile(
    r"^Unable to automatically determine author's name, specify it with --author$"
)
BAD_CHARM_NAME_REGEX = re.compile(
    r" is not a valid charm name. The name must start with a lowercase letter and contain only alphanumeric characters and hyphens.$",
)
VALID_AUTHORS = [
    pytest.param("Author McAuthorFace", id="ascii-author"),
    pytest.param("فلانة الفلانية", id="non-ascii-author"),
]


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
        pytest.param("simple", BASIC_INIT_FILES, id="simple"),
        pytest.param("machine", BASIC_INIT_FILES, id="machine"),
        pytest.param("kubernetes", BASIC_INIT_FILES, id="kubernetes"),
    ],
)
@pytest.mark.parametrize("charm_name", ["my-charm", "charm123"])
@pytest.mark.parametrize("author", VALID_AUTHORS)
def test_files_created_correct(
    new_path,
    init_command,
    profile: str,
    expected_files: set[pathlib.Path],
    charm_name,
    author,
):
    params = create_namespace(name=charm_name, author=author, profile=profile)
    init_command.run(params)

    actual_files = {p.relative_to(new_path) for p in new_path.rglob("*")}

    # Note: we need to specify the encoding here because Windows defaults ta CP-1252.
    charmcraft_yaml = (new_path / "charmcraft.yaml").read_text(encoding="utf-8")
    tox_ini = (new_path / "tox.ini").read_text(encoding="utf-8")

    pytest_check.equal(actual_files, expected_files)
    pytest_check.is_true(re.search(rf"^name: {charm_name}$", charmcraft_yaml, re.MULTILINE))
    pytest_check.is_true(re.search(rf"^# Copyright \d+ {author}", tox_ini))


def test_force(new_path, init_command):
    tmp_file = new_path / "README.md"
    with tmp_file.open("w") as f:
        f.write("This is a nonsense readme")

    init_command.run(create_namespace(force=True))

    # Check that init ran
    assert (new_path / "LICENSE").exists()

    # Check that init did not overwrite files
    with tmp_file.open("r") as f:
        assert f.read() == "This is a nonsense readme"


@pytest.mark.parametrize("name", [None, 0, "1234", "yolo swag", "camelCase"])
def test_bad_name(monkeypatch, new_path, init_command, name):
    with pytest.raises(errors.CraftError, match=BAD_CHARM_NAME_REGEX):
        init_command.run(create_namespace(name=name))


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
@pytest.mark.parametrize("author", VALID_AUTHORS)
def test_gecos_valid_author(monkeypatch, new_path, init_command, author):
    monkeypatch.setattr(
        pwd,
        "getpwuid",
        mock.Mock(
            return_value=pwd.struct_passwd(
                ("user", "pass", 1, 1, f"{author},,,", "homedir", "shell")
            )
        ),
    )

    init_command.run(create_namespace(author=None))

    pytest_check.is_true(
        re.search(rf"^# Copyright \d+ {author}", (new_path / "tox.ini").read_text())
    )


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
@pytest.mark.parametrize(
    ("mock_getpwuid", "error_msg"),
    [
        pytest.param(
            mock.Mock(side_effect=KeyError("no user")),
            UNKNOWN_AUTHOR_REGEX,
            id="user-doesnt-exist",
        ),
    ],
)
def test_gecos_user_not_found(monkeypatch, new_path, init_command, mock_getpwuid, error_msg):
    monkeypatch.setattr(pwd, "getpwuid", mock_getpwuid)

    with pytest.raises(errors.CraftError, match=error_msg):
        init_command.run(create_namespace(author=None))


@pytest.mark.skipif(sys.platform == "win32", reason=("Password database only on Unix"))
def test_gecos_user_has_no_name(monkeypatch, new_path, init_command):
    mock_getpwuid = mock.Mock(
        return_value=pwd.struct_passwd(("user", "pass", 1, 1, "", "dir", "shell"))
    )
    monkeypatch.setattr(pwd, "getpwuid", mock_getpwuid)

    with pytest.raises(errors.CraftError, match=UNKNOWN_AUTHOR_REGEX):
        init_command.run(create_namespace(author=None))


@pytest.mark.parametrize(
    "subdir",
    [
        "somedir",
        "some/dir",
        "a/really/deep/path/with_parents/all/created",
        pytest.param(
            "/tmp/test_charm_dir-absolute_directory_path",
            marks=pytest.mark.skipif(os.name != "posix", reason="This is a posix path"),
        ),
    ],
)
@pytest.mark.parametrize("expected_files", [BASIC_INIT_FILES])
def test_create_directory(new_path, init_command, subdir, expected_files):
    init_dir = new_path / subdir

    try:
        init_command._global_args["project_dir"] = subdir

        init_command.run(create_namespace())

        actual_files = {p.relative_to(init_dir) for p in init_dir.rglob("*")}

        assert actual_files == expected_files

    finally:
        shutil.rmtree(init_dir)


@pytest.mark.skipif(os.name != "posix", reason="Checking posix executable bit.")
def test_executable_set(new_path, init_command):
    init_command.run(create_namespace())

    for path in new_path.rglob(".py"):
        assert path.stat().st_mode & S_IXALL == S_IXALL


@pytest.mark.slow()
@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
@pytest.mark.skipif(bool(os.getenv("RUNNING_TOX")), reason="does not work inside tox")
@pytest.mark.parametrize("profile", list(commands.init.PROFILES))
def test_tox_success(new_path, init_command, profile):
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

    init_command.run(create_namespace(profile=profile))

    result = subprocess.run(
        ["tox", "-v"],
        cwd=new_path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, "Tox run failed:\n" + result.stdout


@pytest.mark.parametrize("profile", list(commands.init.PROFILES))
def test_pep257(new_path, init_command, profile):
    to_ignore = {
        "D105",  # Missing docstring in magic method
        "D107",  # Missing docstring in __init__
    }
    to_include = pydocstyle.violations.conventions.pep257 - to_ignore

    init_command.run(create_namespace(profile=profile))

    python_paths = (str(path) for path in new_path.rglob("*.py"))
    python_paths = (path for path in python_paths if "tests" not in path)
    errors = list(pydocstyle.check(python_paths, select=to_include))

    if errors:
        report = [f"Please fix files as suggested by pydocstyle ({len(errors):d} issues):"]
        report.extend(str(e) for e in errors)
        msg = "\n".join(report)
        pytest.fail(msg, pytrace=False)
