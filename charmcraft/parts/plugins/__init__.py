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

"""Craft-parts plugins and plugin overrides for charmcraft."""

from ._charm import CharmPlugin, CharmPluginProperties
from ._poetry import PoetryPlugin, PoetryPluginProperties
from ._python import PythonPlugin, PythonPluginProperties
from ._reactive import ReactivePlugin, ReactivePluginProperties
from ._uv import UvPlugin
from craft_parts.plugins.uv_plugin import UvPluginProperties

__all__ = [
    "CharmPlugin",
    "CharmPluginProperties",
    "PoetryPlugin",
    "PoetryPluginProperties",
    "PythonPlugin",
    "PythonPluginProperties",
    "ReactivePlugin",
    "ReactivePluginProperties",
    "UvPlugin",
    "UvPluginProperties",
]
