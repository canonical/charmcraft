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
"""Unit tests for the Charmcraft-specific python plugin."""

import pathlib
import shlex
import typing

import pytest

from charmcraft.parts import plugins

PIP = "/python -m pip"


def test_get_build_environment(
    python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    env = python_plugin.get_build_environment()

    assert env["PIP_NO_BINARY"] == ":all:"


def test_get_venv_directory(
    python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    assert python_plugin._get_venv_directory() == install_path / "venv"


@pytest.fixture
def make_python_plugin(make_plugin):
    """Build a python plugin whose pip command is pinned to a known string."""

    def _make(**spec):
        plugin, part_info = make_plugin("python", **spec)
        plugin = typing.cast(plugins.PythonPlugin, plugin)
        plugin._get_pip = lambda: PIP  # ty: ignore[invalid-assignment]
        return plugin, part_info

    return _make


@pytest.mark.parametrize("constraints", [[], ["constraints.txt"]])
@pytest.mark.parametrize("requirements", [[], ["requirements.txt"]])
@pytest.mark.parametrize("packages", [[], ["distro==1.4.0"]])
def test_pip_install_command_carries_part_options(
    make_python_plugin,
    constraints: list[str],
    requirements: list[str],
    packages: list[str],
):
    plugin, _ = make_python_plugin(
        **{
            "python-constraints": constraints,
            "python-requirements": requirements,
            "python-packages": packages,
        }
    )

    install_command, check_command, *_ = plugin._get_package_install_commands()

    assert install_command.startswith(PIP)
    assert check_command.startswith(PIP)
    split_install_command = shlex.split(install_command)
    for constraints_file in constraints:
        assert f"--constraint={constraints_file}" in split_install_command
    for requirements_file in requirements:
        assert f"--requirement={requirements_file}" in split_install_command
    for package in packages:
        assert package in split_install_command


@pytest.mark.parametrize("source_subdir", [None, "subdir"])
def test_build_subdir_follows_source_subdir(
    make_python_plugin, source_subdir: str | None
):
    _, part_info = make_python_plugin(source_subdir=source_subdir)

    if source_subdir:
        assert part_info.part_build_subdir != part_info.part_build_dir
    else:
        assert part_info.part_build_subdir == part_info.part_build_dir


@pytest.mark.parametrize("source_subdir", [None, "subdir"])
@pytest.mark.parametrize(
    ("has_src", "has_lib"),
    [
        (False, False),
        (True, False),
        (True, True),
        (False, True),
    ],
)
def test_copy_commands_follow_existing_directories(
    make_python_plugin,
    copy_command,
    split_copy_commands,
    source_subdir: str | None,
    has_src: bool,
    has_lib: bool,
):
    plugin, part_info = make_python_plugin(source_subdir=source_subdir)
    build_subdir = part_info.part_build_subdir
    if has_src:
        (build_subdir / "src").mkdir(parents=True)
    if has_lib:
        (build_subdir / "lib" / "charm").mkdir(parents=True)

    expected_copies = []
    if has_src:
        expected_copies.append(copy_command(build_subdir / "src"))
    if has_lib:
        expected_copies.append(copy_command(build_subdir / "lib"))

    commands = plugin._get_package_install_commands()

    install_commands, copies = split_copy_commands(commands)
    assert copies == expected_copies
    assert commands == [*install_commands, *copies]


def test_copy_commands_ignore_parent_of_source_subdir(
    make_python_plugin, split_copy_commands
):
    plugin, part_info = make_python_plugin(source_subdir="subdir")
    build_path = part_info.part_build_dir
    (build_path / "src").mkdir(parents=True)
    (build_path / "lib" / "charm").mkdir(parents=True)

    _, copies = split_copy_commands(plugin._get_package_install_commands())

    assert copies == []


def test_get_rm_command(
    python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    assert (
        f"rm -rf {install_path / 'venv/bin'}/!(activate)"
        in python_plugin.get_build_commands()
    )


def test_no_get_rm_command(
    tmp_path, python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    spec = {
        "plugin": "python",
        "source": str(tmp_path),
        "python-keep-bins": True,
    }
    python_plugin._options = plugins.PythonPluginProperties.unmarshal(spec)
    assert (
        f"rm -rf {install_path / 'venv/bin'}/!(activate)"
        not in python_plugin.get_build_commands()
    )
