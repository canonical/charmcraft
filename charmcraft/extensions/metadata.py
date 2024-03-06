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
"""metadata.yaml extension."""
from typing import Any

import craft_application.errors
import craft_application.util
import pydantic
from overrides import override

from charmcraft import const, errors, models, utils
from charmcraft.extensions import extension


class Metadata(extension.Extension):
    """An extension that validates and loads metadata.yaml into a charm.

    We still support having ``metadata.yaml`` separate from ``charmcraft.yaml``,
    so this extension will load that if it exists.
    """

    @override
    @staticmethod
    def get_supported_bases() -> list[tuple[str, str]]:
        """We support all bases."""
        return sorted(const.SUPPORTED_BASES)

    @override
    @staticmethod
    def is_experimental(base: tuple[str, str] | None) -> bool:  # noqa: ARG004
        """Not experimental."""
        return False

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Get additional fields from metadata.yaml."""
        metadata_path = self.project_root / const.METADATA_FILENAME
        if not metadata_path.is_file():
            raise errors.InvalidYamlFileError(
                const.METADATA_FILENAME,
                resolution="Ensure 'metadata.yaml' is a file",
                docs_url="https://juju.is/docs/sdk/metadata-yaml",
            )

        with metadata_path.open() as md_file:
            metadata_dict = craft_application.util.safe_yaml_load(md_file)
        if not isinstance(metadata_dict, dict):
            raise errors.InvalidYamlFileError(
                const.METADATA_FILENAME,
                resolution="Ensure 'metadata.yaml' is a valid YAML dictionary",
                docs_url="https://juju.is/docs/sdk/metadata-yaml",
            )

        try:
            models.CharmMetadataLegacy.unmarshal(metadata_dict)
        except pydantic.ValidationError as exc:
            raise craft_application.errors.CraftValidationError.from_pydantic(
                exc, file_name=const.METADATA_FILENAME
            )

        if duplicate_fields := metadata_dict.keys() & self.yaml_data.keys():
            duplicate_fields_str = utils.humanize_list(duplicate_fields, "and")
            raise errors.CraftError(
                "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
                details=f"Duplicate fields: {duplicate_fields_str}",
                resolution="Remove the duplicate fields from metadata.yaml",
                retcode=65,  # Data error. per sysexits.h
            )

        return metadata_dict

    @override
    def get_part_snippet(self) -> dict[str, Any]:
        """Nothing to add to an existing part."""
        return {}

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Generate the bundle part if there isn't one."""
        return {}
