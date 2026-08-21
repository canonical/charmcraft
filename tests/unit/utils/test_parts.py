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
"""Unit tests for craft-parts utility functions."""

import pathlib
import shlex

import pytest

from charmcraft.utils import parts


def test_extend_python_build_environment():
    base_env = {"FOO": "bar"}
    extended = parts.extend_python_build_environment(base_env)
    assert extended == {
        "FOO": "bar",
        "PARTS_PYTHON_VENV_ARGS": "--without-pip",
    }


def test_get_charm_copy_commands_no_dirs(tmp_path: pathlib.Path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    commands = parts.get_charm_copy_commands(build_dir, install_dir)
    assert commands == []


def test_get_charm_copy_commands_only_src(tmp_path: pathlib.Path):
    build_dir = tmp_path / "build"
    (build_dir / "src").mkdir(parents=True)
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    commands = parts.get_charm_copy_commands(build_dir, install_dir)
    expected_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_dir / 'src'} {install_dir}"
    )
    assert commands == [expected_src_cmd]


def test_get_charm_copy_commands_only_lib(tmp_path: pathlib.Path):
    build_dir = tmp_path / "build"
    (build_dir / "lib").mkdir(parents=True)
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    commands = parts.get_charm_copy_commands(build_dir, install_dir)
    expected_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_dir / 'lib'} {install_dir}"
    )
    assert commands == [expected_lib_cmd]


def test_get_charm_copy_commands_both_src_and_lib(tmp_path: pathlib.Path):
    build_dir = tmp_path / "build"
    (build_dir / "src").mkdir(parents=True)
    (build_dir / "lib").mkdir(parents=True)
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    commands = parts.get_charm_copy_commands(build_dir, install_dir)
    expected_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_dir / 'src'} {install_dir}"
    )
    expected_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_dir / 'lib'} {install_dir}"
    )
    assert commands == [expected_src_cmd, expected_lib_cmd]


def test_get_charm_copy_commands_with_spaces(tmp_path: pathlib.Path):
    build_dir = tmp_path / "build dir with spaces"
    (build_dir / "src").mkdir(parents=True)
    install_dir = tmp_path / "install dir with spaces"
    install_dir.mkdir()

    commands = parts.get_charm_copy_commands(build_dir, install_dir)
    expected_src_cmd = shlex.join(
        [
            "cp",
            "--archive",
            "--recursive",
            "--reflink=auto",
            str(build_dir / "src"),
            str(install_dir),
        ]
    )
    assert commands == [expected_src_cmd]


@pytest.mark.parametrize("keep_bins", [True, False])
def test_get_venv_cleanup_commands(tmp_path: pathlib.Path, keep_bins: bool):
    venv_path = tmp_path / "venv"
    commands = parts.get_venv_cleanup_commands(venv_path, keep_bins=keep_bins)

    assert any("VIRTUAL_ENV=" in cmd for cmd in commands)
    assert any("lib64" in cmd for cmd in commands)
    if keep_bins:
        assert not any("rm -rf" in cmd for cmd in commands)
    else:
        assert any(f"rm -rf {venv_path / 'bin'}/!(activate)" in cmd for cmd in commands)
