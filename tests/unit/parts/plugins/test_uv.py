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

import typing
from pathlib import Path

import craft_parts
import pytest
import pytest_check

from charmcraft.parts import plugins


def test_get_build_environment(uv_plugin: plugins.UvPlugin):
    env = uv_plugin.get_build_environment()

    assert env["PARTS_PYTHON_VENV_ARGS"] == "--without-pip"


def test_get_venv_directory(uv_plugin: plugins.UvPlugin, install_path: Path):
    assert uv_plugin._get_venv_directory() == install_path / "venv"


def test_get_package_install_commands(
    uv_plugin: plugins.UvPlugin, build_path: Path, install_path: Path
):
    copy_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/src {install_path}"
    )

    copy_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/lib {install_path}"
    )

    default_commands = uv_plugin._get_package_install_commands()

    pytest_check.is_not_in(copy_src_cmd, default_commands)
    pytest_check.is_not_in(copy_lib_cmd, default_commands)

    (build_path / "src").mkdir(parents=True)

    pytest_check.equal(
        uv_plugin._get_package_install_commands(), [*default_commands, copy_src_cmd]
    )

    (build_path / "lib" / "charm").mkdir(parents=True)

    pytest_check.equal(
        uv_plugin._get_package_install_commands(),
        [*default_commands, copy_src_cmd, copy_lib_cmd],
    )

    (build_path / "src").rmdir()

    pytest_check.equal(
        uv_plugin._get_package_install_commands(), [*default_commands, copy_lib_cmd]
    )


def test_do_not_install_project(uv_plugin: plugins.UvPlugin) -> None:
    for command in uv_plugin._get_package_install_commands():
        if command.startswith("uv sync") and "--no-install-project" in command:
            break
    else:
        pytest.fail(reason="Charms should not be installed as projects.")


def test_get_package_install_commands_source_subdir(tmp_path: Path, install_path: Path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {"plugin": "uv", "source": str(tmp_path), "source-subdir": "subdir"}
    plugin_properties = plugins.UvPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="uv")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)
    plugin = typing.cast(
        plugins.UvPlugin,
        craft_parts.plugins.get_plugin(
            part=part, part_info=part_info, properties=plugin_properties
        ),
    )

    build_path = part_info.part_build_dir
    build_subdir = part_info.part_build_subdir
    assert build_subdir != build_path

    copy_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_subdir}/src {install_path}"
    )
    copy_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_subdir}/lib {install_path}"
    )
    wrong_copy_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/src {install_path}"
    )
    wrong_copy_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/lib {install_path}"
    )

    # Check if no src or libs exist
    default_commands = plugin._get_package_install_commands()
    pytest_check.is_not_in(copy_src_cmd, default_commands)
    pytest_check.is_not_in(copy_lib_cmd, default_commands)

    # Creating src/lib in parent build_path should not trigger copy
    (build_path / "src").mkdir(parents=True)
    (build_path / "lib" / "charm").mkdir(parents=True)
    commands_with_parent_dirs = plugin._get_package_install_commands()
    pytest_check.is_not_in(wrong_copy_src_cmd, commands_with_parent_dirs)
    pytest_check.is_not_in(wrong_copy_lib_cmd, commands_with_parent_dirs)
    pytest_check.is_not_in(copy_src_cmd, commands_with_parent_dirs)
    pytest_check.is_not_in(copy_lib_cmd, commands_with_parent_dirs)

    # With a src directory in build_subdir
    (build_subdir / "src").mkdir(parents=True)
    pytest_check.equal(
        plugin._get_package_install_commands(), [*default_commands, copy_src_cmd]
    )

    # With both src and lib in build_subdir
    (build_subdir / "lib" / "charm").mkdir(parents=True)
    pytest_check.equal(
        plugin._get_package_install_commands(),
        [*default_commands, copy_src_cmd, copy_lib_cmd],
    )

    # With only lib in build_subdir
    (build_subdir / "src").rmdir()
    pytest_check.equal(
        plugin._get_package_install_commands(), [*default_commands, copy_lib_cmd]
    )
