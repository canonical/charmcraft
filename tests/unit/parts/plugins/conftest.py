# Copyright 2026 Canonical Ltd.
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
"""Shared fixtures for plugin unit tests."""

import pathlib
import typing
from collections.abc import Callable

import craft_parts
import pytest

from charmcraft.parts import plugins

PLUGIN_PROPERTIES = {
    "python": plugins.PythonPluginProperties,
    "poetry": plugins.PoetryPluginProperties,
    "uv": plugins.UvPluginProperties,
}

MakePlugin = Callable[..., tuple[craft_parts.plugins.Plugin, craft_parts.PartInfo]]
"""Signature of the ``make_plugin`` factory fixture."""


@pytest.fixture
def make_plugin(tmp_path: pathlib.Path) -> MakePlugin:
    """Build a plugin with its part info from a partial part spec.

    Returns a factory so each test declares exactly the spec it asserts on:
    the plugin name, an optional ``source-subdir`` and any extra part keys.
    """

    def _make_plugin(
        plugin_name: str,
        *,
        source_subdir: str | None = None,
        **spec_extra: typing.Any,
    ) -> tuple[craft_parts.plugins.Plugin, craft_parts.PartInfo]:
        project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
        spec: dict[str, typing.Any] = {
            "plugin": plugin_name,
            "source": str(tmp_path),
            **spec_extra,
        }
        if source_subdir:
            spec["source-subdir"] = source_subdir
        plugin_properties = PLUGIN_PROPERTIES[plugin_name].unmarshal(spec)
        part_spec = craft_parts.plugins.extract_part_properties(
            spec, plugin_name=plugin_name
        )
        part = craft_parts.Part(
            "foo",
            part_spec,
            project_dirs=project_dirs,
            plugin_properties=plugin_properties,
        )
        project_info = craft_parts.ProjectInfo(
            application_name="test",
            project_dirs=project_dirs,
            cache_dir=tmp_path,
        )
        part_info = craft_parts.PartInfo(project_info=project_info, part=part)
        plugin = craft_parts.plugins.get_plugin(
            part=part, part_info=part_info, properties=plugin_properties
        )
        return plugin, part_info

    return _make_plugin


COPY_COMMAND_PREFIX = "cp "


@pytest.fixture
def split_copy_commands() -> Callable[[list[str]], tuple[list[str], list[str]]]:
    """Split install commands from independently identified copy commands.

    Classification uses only the executable name so helper-owned flags are not
    duplicated while extra copy commands remain visible.
    """

    def _split(commands: list[str]) -> tuple[list[str], list[str]]:
        copies = [cmd for cmd in commands if cmd.startswith(COPY_COMMAND_PREFIX)]
        install = [cmd for cmd in commands if not cmd.startswith(COPY_COMMAND_PREFIX)]
        return install, copies

    return _split
