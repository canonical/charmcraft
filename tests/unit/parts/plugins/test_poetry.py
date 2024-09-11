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
"""Unit tests for the Charmcraft-specific poetry plugin."""

import pathlib

import craft_parts
import pytest
import pytest_check
from craft_parts.plugins.poetry_plugin import PoetryPluginProperties

from charmcraft.parts import plugins
from charmcraft.parts.plugins._poetry import POETRY_INSTALL_COMMAND


@pytest.fixture
def poetry(tmp_path: pathlib.Path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {
        "plugin": "poetry",
        "source": str(tmp_path),
    }
    plugin_properties = PoetryPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="poetry")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)

    return craft_parts.plugins.get_plugin(
        part=part, part_info=part_info, properties=plugin_properties
    )


@pytest.fixture
def build_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "parts" / "foo" / "build"


@pytest.fixture
def install_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "parts" / "foo" / "install"


def test_get_build_environment(poetry_plugin: plugins.PoetryPlugin, install_path: pathlib.Path):
    env = poetry_plugin.get_build_environment()

    assert env["PIP_NO_BINARY"] == ":all:"
    assert env["PATH"] == f"${{HOME}}/.local/bin:{install_path}/bin:${{PATH}}"


def test_get_build_packages(poetry_plugin: plugins.PoetryPlugin):
    assert "curl" in poetry_plugin.get_build_packages()


def test_get_pull_commands(poetry_plugin: plugins.PoetryPlugin):
    poetry_plugin._system_has_poetry = lambda: False

    assert poetry_plugin.get_pull_commands()[-1] == POETRY_INSTALL_COMMAND


def test_get_venv_directory(poetry_plugin: plugins.PoetryPlugin, install_path: pathlib.Path):
    assert poetry_plugin._get_venv_directory() == install_path / "venv"


def test_get_package_install_commands(
    poetry_plugin: plugins.PoetryPlugin, build_path: pathlib.Path, install_path: pathlib.Path
):
    copy_src_cmd = f"cp --archive --recursive --reflink=auto {build_path}/src {install_path}"
    copy_lib_cmd = f"cp --archive --recursive --reflink=auto {build_path}/lib {install_path}"

    # Check if no src or libs exist
    default_commands = poetry_plugin._get_package_install_commands()

    pytest_check.is_not_in(copy_src_cmd, default_commands)
    pytest_check.is_not_in(copy_lib_cmd, default_commands)

    # With a src directory
    (build_path / "src").mkdir(parents=True)

    pytest_check.equal(
        poetry_plugin._get_package_install_commands(), [*default_commands, copy_src_cmd]
    )

    # With both src and lib
    (build_path / "lib" / "charm").mkdir(parents=True)

    pytest_check.equal(
        poetry_plugin._get_package_install_commands(),
        [*default_commands, copy_src_cmd, copy_lib_cmd],
    )

    # With only lib
    (build_path / "src").rmdir()

    pytest_check.equal(
        poetry_plugin._get_package_install_commands(), [*default_commands, copy_lib_cmd]
    )
