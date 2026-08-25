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

import craft_parts
import pytest
import pytest_check

from charmcraft.parts import plugins


def test_get_build_environment(
    python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    env = python_plugin.get_build_environment()

    assert env["PIP_NO_BINARY"] == ":all:"


def test_get_venv_directory(
    python_plugin: plugins.PythonPlugin, install_path: pathlib.Path
):
    assert python_plugin._get_venv_directory() == install_path / "venv"


@pytest.mark.parametrize("constraints", [[], ["constraints.txt"]])
@pytest.mark.parametrize("requirements", [[], ["requirements.txt"]])
@pytest.mark.parametrize("packages", [[], ["distro==1.4.0"]])
@pytest.mark.parametrize("source_subdir", [None, "subdir"])
def test_get_package_install_commands(
    tmp_path: pathlib.Path,
    install_path: pathlib.Path,
    constraints: list[str],
    requirements: list[str],
    packages: list[str],
    source_subdir: str | None,
    check,
):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec: dict[str, typing.Any] = {
        "plugin": "python",
        "source": str(tmp_path),
        "python-constraints": constraints,
        "python-requirements": requirements,
        "python-packages": packages,
    }
    if source_subdir:
        spec["source-subdir"] = source_subdir
    plugin_properties = plugins.PythonPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="python")
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
        plugins.PythonPlugin,
        craft_parts.plugins.get_plugin(
            part=part, part_info=part_info, properties=plugin_properties
        ),
    )
    plugin._get_pip = lambda: "/python -m pip"  # ty: ignore[invalid-assignment]

    build_path = part_info.part_build_dir
    build_subdir = part_info.part_build_subdir
    if source_subdir:
        assert build_subdir != build_path
    else:
        assert build_subdir == build_path

    copy_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_subdir}/src {install_path}"
    )
    copy_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_subdir}/lib {install_path}"
    )

    actual = plugin._get_package_install_commands()

    with check():
        assert actual[0].startswith("/python -m pip")
    with check():
        assert actual[1].startswith("/python -m pip")
    split_install_command = shlex.split(actual[0])
    for constraints_file in constraints:
        pytest_check.is_in(f"--constraint={constraints_file}", split_install_command)
    for requirements_file in requirements:
        pytest_check.is_in(f"--requirement={requirements_file}", split_install_command)
    for package in packages:
        pytest_check.is_in(package, split_install_command)
    pytest_check.is_not_in(copy_src_cmd, actual)
    pytest_check.is_not_in(copy_lib_cmd, actual)

    if source_subdir:
        (build_path / "src").mkdir(parents=True)
        (build_path / "lib" / "charm").mkdir(parents=True)
        wrong_copy_src_cmd = (
            f"cp --archive --recursive --reflink=auto {build_path}/src {install_path}"
        )
        wrong_copy_lib_cmd = (
            f"cp --archive --recursive --reflink=auto {build_path}/lib {install_path}"
        )
        commands_with_parent_dirs = plugin._get_package_install_commands()
        pytest_check.is_not_in(wrong_copy_src_cmd, commands_with_parent_dirs)
        pytest_check.is_not_in(wrong_copy_lib_cmd, commands_with_parent_dirs)
        pytest_check.is_not_in(copy_src_cmd, commands_with_parent_dirs)
        pytest_check.is_not_in(copy_lib_cmd, commands_with_parent_dirs)

    (build_subdir / "src").mkdir(parents=True)

    pytest_check.is_in(copy_src_cmd, plugin._get_package_install_commands())
    pytest_check.is_not_in(copy_lib_cmd, plugin._get_package_install_commands())

    (build_subdir / "lib" / "charm").mkdir(parents=True)

    pytest_check.is_in(copy_src_cmd, plugin._get_package_install_commands())
    pytest_check.is_in(copy_lib_cmd, plugin._get_package_install_commands())

    (build_subdir / "src").rmdir()

    pytest_check.is_not_in(copy_src_cmd, plugin._get_package_install_commands())
    pytest_check.is_in(copy_lib_cmd, plugin._get_package_install_commands())


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
