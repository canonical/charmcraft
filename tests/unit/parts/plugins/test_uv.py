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

from pathlib import Path

import pytest
import pytest_check

from charmcraft.parts import plugins


def test_get_build_environment(uv_plugin: plugins.UvPlugin):
    env = uv_plugin.get_build_environment()

    assert env["PARTS_PYTHON_VENV_ARGS"] == "--without-pip"


def test_get_venv_directory(uv_plugin: plugins.UvPlugin, install_path: Path):
    assert uv_plugin._get_venv_directory() == install_path / "venv"


@pytest.mark.parametrize("source_subdir", [None, "subdir"])
def test_build_subdir_follows_source_subdir(make_plugin, source_subdir: str | None):
    _, part_info = make_plugin("uv", source_subdir=source_subdir)

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
    make_plugin,
    copy_command,
    split_copy_commands,
    source_subdir: str | None,
    has_src: bool,
    has_lib: bool,
):
    plugin, part_info = make_plugin("uv", source_subdir=source_subdir)
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
    pytest_check.equal(copies, expected_copies)
    pytest_check.equal(commands, [*install_commands, *copies])


def test_copy_commands_ignore_parent_of_source_subdir(make_plugin, split_copy_commands):
    plugin, part_info = make_plugin("uv", source_subdir="subdir")
    build_path = part_info.part_build_dir
    (build_path / "src").mkdir(parents=True)
    (build_path / "lib" / "charm").mkdir(parents=True)

    _, copies = split_copy_commands(plugin._get_package_install_commands())
    pytest_check.equal(copies, [])


def test_do_not_install_project(uv_plugin: plugins.UvPlugin) -> None:
    for command in uv_plugin._get_package_install_commands():
        if command.startswith("uv sync") and "--no-install-project" in command:
            break
    else:
        pytest.fail(reason="Charms should not be installed as projects.")
