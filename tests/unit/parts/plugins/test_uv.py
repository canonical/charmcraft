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
