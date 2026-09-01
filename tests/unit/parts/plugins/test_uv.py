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
    assert "UV_CACHE_DIR" in env


def test_get_venv_directory(uv_plugin: plugins.UvPlugin, install_path: Path):
    assert uv_plugin._get_venv_directory() == install_path / "venv"


@pytest.mark.parametrize("source_subdir", [None, "subdir"])
def test_get_package_install_commands(
    tmp_path: Path,
    install_path: Path,
    source_subdir: str | None,
):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec: dict[str, typing.Any] = {
        "plugin": "uv",
        "source": str(tmp_path),
    }
    if source_subdir:
        spec["source-subdir"] = source_subdir
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

    default_commands = plugin._get_package_install_commands()

    pytest_check.is_not_in(copy_src_cmd, default_commands)
    pytest_check.is_not_in(copy_lib_cmd, default_commands)

    if source_subdir:
        # Creating src/lib in parent build_path should not trigger copy
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

    pytest_check.equal(
        plugin._get_package_install_commands(), [*default_commands, copy_src_cmd]
    )

    (build_subdir / "lib" / "charm").mkdir(parents=True)

    pytest_check.equal(
        plugin._get_package_install_commands(),
        [*default_commands, copy_src_cmd, copy_lib_cmd],
    )

    (build_subdir / "src").rmdir()

    pytest_check.equal(
        plugin._get_package_install_commands(), [*default_commands, copy_lib_cmd]
    )


def test_do_not_install_project(uv_plugin: plugins.UvPlugin) -> None:
    for command in uv_plugin._get_package_install_commands():
        if command.startswith("uv sync") and "--no-install-project" in command:
            break
    else:
        pytest.fail(reason="Charms should not be installed as projects.")


def test_uv_cache_dir_set(uv_plugin: plugins.UvPlugin, tmp_path: Path) -> None:
    """Test that UV_CACHE_DIR is set to enable wheel caching."""
    env = uv_plugin.get_build_environment()

    # UV_CACHE_DIR should be set to the part's cache directory
    # to ensure wheels built from source (when no-binary=true) are cached
    assert "UV_CACHE_DIR" in env, "UV_CACHE_DIR should be set in build environment"

    # The cache dir should point to a uv subdirectory in the part's cache
    cache_dir = Path(env["UV_CACHE_DIR"])
    assert cache_dir.name == "uv", (
        f"UV_CACHE_DIR should point to 'uv' subdirectory, got {cache_dir.name}"
    )
