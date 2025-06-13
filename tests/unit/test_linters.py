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
import string
import subprocess
import sys

import pytest
from hypothesis import given, strategies

from charmcraft import linters
from charmcraft.models.lint import LintResult


@given(
    name=strategies.text(
        strategies.characters(
            codec="ascii",  # Only ASCII characters are valid in Python names
            categories=["L", "N"],  # Letters and numbers
            include_characters="._-",  # Or hyphens, underscores, periods
        ),
        min_size=1,  # At least one character
    ).filter(lambda x: x[0] not in "._-" and x[-1] not in "._-"),
    next_char=strategies.sampled_from(string.whitespace + "<>=~!"),
    further_garbage=strategies.text(),
)
def test_fuzz_python_name_regex(name, next_char, further_garbage):
    assert linters.PYTHON_NAME_REGEX.match(name).group(0) == name
    assert linters.PYTHON_NAME_REGEX.match(f"{name}{next_char}").group(0) == name
    assert (
        linters.PYTHON_NAME_REGEX.match(f"{name}{next_char}{further_garbage}").group(0)
        == name
    )


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        (
            r'requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"',
            "2.8.1",
        ),
        (">=1.0.0", "1.0.0"),
    ],
)
def test_min_version_regex_matches(string, expected):
    assert linters.MIN_VERSION_REGEX.search(string).group(1) == expected


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        (
            r'requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"',
            "2.8",
        ),
        ("~=1.0.0", "1.0"),
    ],
)
def test_approx_version_regex_matches(string, expected):
    assert expected in linters.APPROX_VERSION_REGEX.search(string).group(1, 2)


@pytest.mark.parametrize(
    ("string", "expected"),
    [("==1.0.0", "1.0.0")],
)
def test_exact_version_regex_matches(string, expected):
    assert linters.EXACT_VERSION_REGEX.search(string).group(1) == expected


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


def test_pip_check_success(valid_venv_path: pathlib.Path, fp):
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=0,
        stdout="Loo loo loo, doing pip stuff. Pip stuff is my favourite stuff.",
    )

    lint = linters.PipCheck()
    assert lint.run(valid_venv_path) == LintResult.OK
    assert lint.text == linters.PipCheck.text


def test_pip_check_warning(valid_venv_path: pathlib.Path, fp):
    fp.register(
        [sys.executable, "-m", "pip", "--python", fp.any(), "check"],
        returncode=1,
        stdout="This error was sponsored by Raytheon Knife Missiles™",
    )

    lint = linters.PipCheck()
    assert lint.run(valid_venv_path) == LintResult.WARNING
    assert lint.text == "This error was sponsored by Raytheon Knife Missiles™"


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


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("cryptography", "cryptography"),
        (
            "opentelemetry.exporter.otlp.proto.http",
            "opentelemetry_exporter_otlp_proto_http",
        ),
        ("poetry-core", "poetry_core"),
    ],
)
def test_pydeps_fs(name, expected):
    assert linters.PyDeps.convert_to_fs(name) == expected


@pytest.mark.parametrize(
    ("spec", "version", "expected"),
    [
        (">=1.0.0", (1, 0, 0), True),
        (">= 2.0.0, == 1.2.3, ==1.2.4, ~=1.4.0", (1, 2, 3), True),
        (">= 2.0.0, == 1.2.3, ==1.2.4, ~=1.4.0", (1, 2, 4), True),
        (">= 2.0.0, == 1.2.3, ==1.2.4, ~=1.4.0, ==1.5.*", (1, 4, 10), True),
        ("==1.5.*", (1, 5, 10), True),
        (">= 2.0.0, == 1.2.3, ==1.2.4, ~=1.4.0", (2, 2, 4), True),
    ],
)
def test_pydeps_version_matches(spec, version, expected):
    assert linters.PyDeps.version_matches(spec, version) == expected


@pytest.mark.parametrize(
    ("deps", "expected"),
    [
        (set(), (set(), set())),
        ({"existing"}, (set(), set())),
        ({"existing.child.package>=1.0.0"}, (set(), set())),
        ({"existing.child.package==1.0.0"}, (set(), {"existing.child.package==1.0.0"})),
        ({"existing-package"}, (set(), set())),
        ({"existing-module"}, (set(), set())),
        ({"nope"}, ({"nope"}, set())),
    ],
)
def test_pydeps_get_missing_deps(tmp_path, mocker, deps, expected):
    packages_path = tmp_path / "lib/python3.14/site-packages"
    (packages_path / "existing").mkdir(parents=True)
    (packages_path / "existing_child_package-1.0.1.dist-info").mkdir(parents=True)
    (packages_path / "existing_package").mkdir(parents=True)
    (packages_path / "existing_module.py").touch()

    assert linters.PyDeps._get_missing_deps(deps, tmp_path) == expected
