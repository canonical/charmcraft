# Copyright 2021-2023 Canonical Ltd.
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

"""Craft-parts setup, lifecycle and plugins."""

from typing import Any

from craft_parts import plugins
from craft_parts.parts import PartSpec

from charmcraft.parts.bundle import BundlePlugin
from charmcraft.parts.charm import CharmPlugin, CharmPluginProperties
from charmcraft.parts.lifecycle import PartsLifecycle
from charmcraft.parts.reactive import ReactivePlugin, ReactivePluginProperties

__all__ = [
    "CharmPlugin",
    "CharmPluginProperties",
    "ReactivePlugin",
    "ReactivePluginProperties",
    "setup_parts",
    "process_part_config",
    "PartsLifecycle",
]


def setup_parts():
    """Initialize craft-parts plugins."""
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})


def process_part_config(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and fill the given part data against/with common and plugin models.

    :param data: The part data to use.

    :return: The part data validated and completed with plugin defaults.
    """
    if not isinstance(data, dict):
        raise TypeError("value must be a dictionary")

    # copy the original data, we'll modify it
    spec = data.copy()

    plugin_name = spec.get("plugin")
    if not plugin_name:
        raise ValueError("'plugin' not defined")

    plugin_class = plugins.get_plugin_class(plugin_name)

    # validate plugin properties
    plugin_properties = plugin_class.properties_class.unmarshal(spec)

    # validate common part properties
    part_spec = plugins.extract_part_properties(spec, plugin_name=plugin_name)
    PartSpec(**part_spec)

    # get plugin properties data if it's model based (otherwise it's empty), and
    # update with the received config
    if isinstance(plugin_properties, plugins.PluginProperties):
        full_config = plugin_properties.model_dump(by_alias=True, exclude_unset=True)
    else:
        full_config = {}
    full_config.update(data)

    return full_config
