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
"""Extensions that load additional YAML files into the project."""
import collections
from typing import Any

import craft_application.errors
import craft_application.models
import craft_application.util
import pydantic
from overrides import override

from charmcraft import const, errors, models, utils
from charmcraft.extensions import extension


class _ConfigFile(extension.Extension):
    """Base extension for updating the Charmcraft project from a config file."""

    filename: str
    docs_url: str
    config_model: type[craft_application.models.CraftBaseModel]

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

    def _get_config_file(self) -> dict[str, Any]:
        """Load the configuration file."""
        config_path = self.project_root / self.filename
        if not config_path.is_file():
            raise errors.InvalidYamlFileError(
                self.filename,
                resolution=f"Ensure {self.filename!r} is a file",
                docs_url=self.docs_url,
            )

        with config_path.open() as md_file:
            config_dict = craft_application.util.safe_yaml_load(md_file)
        if not isinstance(config_dict, dict):
            raise errors.InvalidYamlFileError(
                self.filename,
                resolution=f"Ensure {self.filename!r} is a valid YAML dictionary",
                docs_url=self.docs_url,
            )

        try:
            self.config_model.unmarshal(config_dict)
        except pydantic.ValidationError as exc:
            raise craft_application.errors.CraftValidationError.from_pydantic(
                exc, file_name=self.filename
            )

        if duplicate_fields := config_dict.keys() & self.yaml_data.keys():
            duplicate_fields_str = utils.humanize_list(duplicate_fields, "and")
            raise errors.CraftError(
                f"Fields in charmcraft.yaml cannot be duplicated in {self.filename!r}",
                details=f"Duplicate fields: {duplicate_fields_str}",
                resolution=f"Remove the duplicate fields from {self.filename!r}",
                retcode=65,  # Data error. per sysexits.h
            )

        return config_dict

    @override
    def get_part_snippet(self) -> dict[str, Any]:
        """Nothing to add to an existing part."""
        return {}

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Generate the bundle part if there isn't one."""
        return {}


class Config(_ConfigFile):
    """An extension that validates and loads config.yaml into a charm.

    We still support having ``config.yaml`` separate from ``charmcraft.yaml``,
    so this extension will load that if it exists.
    """

    filename = const.JUJU_CONFIG_FILENAME
    docs_url = "https://juju.is/docs/sdk/config-yaml"
    config_model = models.JujuConfig

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Get the root snippet for config."""
        return {"config": self._get_config_file()}


class Metadata(_ConfigFile):
    """An extension that validates and loads metadata.yaml into a charm.

    We still support having ``metadata.yaml`` separate from ``charmcraft.yaml``,
    so this extension will load that if it exists.
    """

    filename = const.METADATA_FILENAME
    docs_url = "https://juju.is/docs/sdk/metadata-yaml"
    config_model = models.CharmMetadataLegacy

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        return self._get_config_file()


class Actions(_ConfigFile):
    """An extension that validates and loads metadata.yaml into a charm.

    We still support having ``metadata.yaml`` separate from ``charmcraft.yaml``,
    so this extension will load that if it exists.
    """

    filename = const.JUJU_ACTIONS_FILENAME
    docs_url = "https://juju.is/docs/sdk/actions-yaml"

    @staticmethod
    def unmarshal(data: dict[str, dict[str, Any]]) -> models.JujuActions:
        return models.JujuActions.unmarshal({"actions": data})

    config_model = collections.namedtuple("config_model", "unmarshal")(unmarshal)

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        return {"actions": self._get_config_file()}


class _FlexibleModel(craft_application.models.CraftBaseModel, extra=pydantic.Extra.allow):
    """A model that can have anything. We don't need to validate bundle models."""


class Bundle(_ConfigFile):
    """An extension that generates the bits for a bundle.

    This extension should never be used directly. It will be applied automatically
    when relevant.
    """

    filename = const.BUNDLE_FILENAME
    docs_url = "https://juju.is/docs/sdk/charm-bundles"
    config_model = _FlexibleModel

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        bundle_config = self._get_config_file()
        snippet = {"bundle": bundle_config}

        for attribute in models.Bundle.__fields__:
            if attribute in bundle_config and attribute not in self.yaml_data:
                snippet[attribute] = bundle_config[attribute]

        return snippet

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Generate the bundle part if there isn't one."""
        parts = self.yaml_data.get("parts", {})
        has_bundle = any(part.get("plugin") == "bundle" for part in parts.values())
        if has_bundle:
            return {}

        return {"bundle": {"plugin": "bundle", "source": "."}}
