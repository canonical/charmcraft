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
"""Bundle extension."""
from typing import Any

from overrides import override

from charmcraft.extensions import extension


class Bundle(extension.Extension):
    """An extension that generates the bits for a bundle."""

    @override
    @staticmethod
    def get_supported_bases() -> list[tuple[str, str]]:
        """Bundles don't have bases."""
        return []

    @override
    @staticmethod
    def is_experimental(base: tuple[str, str] | None) -> bool:  # noqa: ARG004
        """Bundles are never experimental."""
        return False

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """No root snippet to add."""
        return {}

    @override
    def get_part_snippet(self) -> dict[str, Any]:
        """Nothing to add to an existing part."""
        return {}

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Generate the bundle part if there isn't one."""
        parts = self.yaml_data.get("parts", {})
        has_bundle = any(part.get("plugin") == "bundle" for part in parts.values())
        if has_bundle:
            return {}

        return {"bundle": {"plugin": "bundle", "source": "."}}
