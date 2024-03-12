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
"""Pre-processing functions for charmcraft projects.

These functions are called from the Application class's `_extra_yaml_transform`
to do pre-processing on a charmcraft.yaml file before applying extensions.
"""
from typing import Any


def add_default_parts(yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Apply the expected default parts to a project if it doesn't contain any.

    :param yaml_data: The raw YAML dictionary of the project.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    if (yaml_data.get("type")) != "bundle":
        return yaml_data
    parts = yaml_data.setdefault("parts", {})
    if parts:  # Only operate if there aren't any parts declared.
        return yaml_data

    parts["bundle"] = {"plugin": "bundle", "source": "."}
    return yaml_data
