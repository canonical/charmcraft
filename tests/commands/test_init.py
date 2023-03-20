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
import os
import subprocess
import sys
from argparse import Namespace
from unittest.mock import patch

import pytest
from craft_cli import CraftError

from charmcraft.commands.init import InitCommand, DEFAULT_PROFILE, PROFILES
from charmcraft.config import Project
from charmcraft.utils import S_IXALL
from tests.test_infra import pep8_test, get_python_filepaths, pep257_test


@pytest.fixture
def mock_pwd():
    with patch("charmcraft.commands.init.pwd", autospec=True) as mock_pwd:
        mock_pwd.getpwuid.return_value.pw_gecos = "Test Gecos Author Name,,,"
        yield mock_pwd


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


def test_init_non_ascii_author(tmp_path, config):
    test_init_pep8(tmp_path, config, author="فلانة الفلانية", profile=DEFAULT_PROFILE)


def test_all_the_files_simple(tmp_path, config):
    cmd = InitCommand(config)
    cmd.run(create_namespace())
    assert {str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*")} == {
        ".gitignore",
        "charmcraft.yaml",
        "CONTRIBUTING.md",
        "LICENSE",
        "config.yaml",
        "metadata.yaml",
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        "src",
        os.path.join("src", "charm.py"),
        "tests",
        os.path.join("tests", "integration"),
        os.path.join("tests", "integration", "__init__.py"),
        os.path.join("tests", "integration", "test_charm.py"),
        os.path.join("tests", "unit"),
        os.path.join("tests", "unit", "__init__.py"),
        os.path.join("tests", "unit", "test_charm.py"),
        "tox.ini",
    }


def test_all_the_files_kubernetes(tmp_path, config):
    cmd = InitCommand(config)
    cmd.run(create_namespace(profile="kubernetes"))
    assert {str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*")} == {
        ".gitignore",
        "charmcraft.yaml",
        "CONTRIBUTING.md",
        "LICENSE",
        "metadata.yaml",
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        "src",
        os.path.join("src", "charm.py"),
        "tests",
        os.path.join("tests", "integration"),
        os.path.join("tests", "integration", "__init__.py"),
        os.path.join("tests", "integration", "test_charm.py"),
        os.path.join("tests", "unit"),
        os.path.join("tests", "unit", "__init__.py"),
        os.path.join("tests", "unit", "test_charm.py"),
        "tox.ini",
    }


def test_all_the_files_machine(tmp_path, config):
    cmd = InitCommand(config)
    cmd.run(create_namespace(profile="machine"))
    assert {str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*")} == {
        ".gitignore",
        "charmcraft.yaml",
        "CONTRIBUTING.md",
        "LICENSE",
        "metadata.yaml",
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        "src",
        os.path.join("src", "charm.py"),
        "tests",
        os.path.join("tests", "integration"),
        os.path.join("tests", "integration", "__init__.py"),
        os.path.join("tests", "integration", "test_charm.py"),
        os.path.join("tests", "unit"),
        os.path.join("tests", "unit", "__init__.py"),
        os.path.join("tests", "unit", "test_charm.py"),
        "tox.ini",
    }


def test_force(tmp_path, config):
    cmd = InitCommand(config)
    tmp_file = tmp_path / "README.md"
    with tmp_file.open("w") as f:
        f.write("This is a nonsense readme")
    cmd.run(create_namespace(force=True))

    # Check that init ran
    assert (tmp_path / "LICENSE").exists()

    # Check that init did not overwrite files
    with tmp_file.open("r") as f:
        assert f.read() == "This is a nonsense readme"


def test_bad_name(config):
    cmd = InitCommand(config)
    with pytest.raises(CraftError):
        cmd.run(create_namespace(name="1234"))


@pytest.mark.skipif(sys.platform == "win32", reason="mocking for pwd/gecos only")
def test_no_author_gecos(tmp_path, config, mock_pwd):
    cmd = InitCommand(config)
    cmd.run(create_namespace(author=None))

    text = (tmp_path / "src" / "charm.py").read_text()
    assert "Test Gecos Author Name" in text


def test_executables(tmp_path, config):
    cmd = InitCommand(config)
    cmd.run(create_namespace())

    if os.name == "posix":
        assert (tmp_path / "src/charm.py").stat().st_mode & S_IXALL == S_IXALL


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
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


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_gecos_missing_in_getpwuid_response(config):
    """No GECOS field in getpwuid response."""
    import pwd

    cmd = InitCommand(config)

    with patch("pwd.getpwuid") as mock_pwd:
        # return a fack passwd struct with an empty gecos (5th parameter)
        mock_pwd.return_value = pwd.struct_passwd(("user", "pass", 1, 1, "", "dir", "shell"))
        msg = "Unable to automatically determine author's name, specify it with --author"
        with pytest.raises(CraftError, match=msg):
            cmd.run(create_namespace(author=None))


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_gecos_missing_user_information(config):
    """No information at all for the requested user."""
    cmd = InitCommand(config)

    with patch("pwd.getpwuid") as mock_pwd:
        mock_pwd.side_effect = KeyError("no user")
        msg = "Unable to automatically determine author's name, specify it with --author"
        with pytest.raises(CraftError, match=msg):
            cmd.run(create_namespace(author=None))


def test_missing_directory(tmp_path, config):
    """If the indicated directory does not exist, create it."""
    init_dir = tmp_path / "foo" / "bar"
    config.set(
        project=Project(
            config_provided=False,
            dirpath=init_dir,
            started_at=datetime.datetime.utcnow(),
        )
    )

    cmd = InitCommand(config)
    cmd.run(create_namespace())

    # check it run ok
    assert (init_dir / "LICENSE").exists()
