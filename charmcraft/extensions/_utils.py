# Copyright 2023 Canonical Ltd.
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

"""Extension application helpers."""

import copy
from pathlib import Path
from typing import Any, cast

from charmcraft.extensions.extension import Extension
from charmcraft.extensions.registry import get_extension_class


def apply_extensions(project_root: Path, yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Apply all extensions.

    :param dict yaml_data: Loaded, unprocessed charmcraft.yaml
    :returns: Modified charmcraft.yaml data with extensions applied
    """
    # Don't modify the dict passed in
    yaml_data = copy.deepcopy(yaml_data)
    declared_extensions: list[str] = cast(list[str], yaml_data.get("extensions", []))
    if not declared_extensions:
        return yaml_data

    del yaml_data["extensions"]

    # Process extensions in a consistent order
    for extension_name in sorted(declared_extensions):
        extension_class = get_extension_class(extension_name)
        extension = extension_class(project_root=project_root, yaml_data=copy.deepcopy(yaml_data))
        extension.validate(extension_name=extension_name)
        _apply_extension(yaml_data, extension)
    return yaml_data


def _apply_extension(
    yaml_data: dict[str, Any],
    extension: Extension,
) -> None:
    # Apply the root components of the extension (if any)
    root_extension = extension.get_root_snippet()
    for property_name, property_value in root_extension.items():
        yaml_data[property_name] = _apply_extension_property(
            yaml_data.get(property_name), property_value
        )

    # Next, apply the part-specific components
    part_extension = extension.get_part_snippet()
    if "parts" not in yaml_data:
        yaml_data["parts"] = {}

    parts = yaml_data["parts"]
    for _, part_definition in parts.items():
        for property_name, property_value in part_extension.items():
            part_definition[property_name] = _apply_extension_property(
                part_definition.get(property_name), property_value
            )

    # Finally, add any parts specified in the extension
    parts_snippet = extension.get_parts_snippet()
    parts_names = (pn for pn in parts_snippet if pn not in yaml_data["parts"])
    for part_name in parts_names:
        parts[part_name] = parts_snippet[part_name]


def _apply_extension_property(
    existing_property: dict | list, extension_property: dict | list
) -> dict | list:
    if existing_property:
        # If the property is not scalar, merge them
        if isinstance(existing_property, list) and isinstance(extension_property, list):
            merged = extension_property + existing_property

            # If the lists are just strings, remove duplicates.
            if all(isinstance(item, str) for item in merged):
                return _remove_list_duplicates(merged)

            return merged

        if isinstance(existing_property, dict) and isinstance(extension_property, dict):
            for key, value in extension_property.items():
                existing_property[key] = _apply_extension_property(
                    existing_property.get(key), value
                )
            return existing_property
        return existing_property

    return extension_property


def _remove_list_duplicates(seq: list[str]) -> list[str]:
    """De-dupe string list maintaining ordering."""
    seen: set[str] = set()
    deduped: list[str] = []

    for item in seq:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    return deduped
