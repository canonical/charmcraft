# Copyright 2023-2024 Canonical Ltd.
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

"""Charmcraft configuration pydantic model."""
import datetime
import os
import pathlib
from typing import Any, Literal, cast

import pydantic
from craft_cli import CraftError
from typing_extensions import Self

from charmcraft import const, parts
from charmcraft.extensions import apply_extensions
from charmcraft.format import format_pydantic_errors
from charmcraft.metafiles.actions import parse_actions_yaml
from charmcraft.metafiles.config import parse_config_yaml
from charmcraft.metafiles.metadata import (
    parse_bundle_metadata_yaml,
    parse_charm_metadata_yaml,
)
from charmcraft.models.actions import JujuActions
from charmcraft.models.basic import AttributeName, LinterName, ModelConfigDefaults
from charmcraft.models.config import JujuConfig
from charmcraft.utils import get_host_architecture


class CharmhubConfig(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Definition of Charmhub endpoint configuration."""

    api_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://api.charmhub.io")
    storage_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://storage.snapcraftcontent.com")
    registry_url: pydantic.HttpUrl = cast(pydantic.HttpUrl, "https://registry.jujucharms.com")


class Base(ModelConfigDefaults):
    """Represents a base."""

    name: pydantic.StrictStr
    channel: pydantic.StrictStr
    architectures: list[pydantic.StrictStr] = [get_host_architecture()]

    @classmethod
    def from_str_and_arch(cls, base_str: str, architectures: list[str]) -> Self:
        """Get a Base from a base string and list of architectures.

        :param base_str: A base string along the lines of "<name>@<channel>"
        :param architectures: A list of architectures (or ["all"])
        """
        name, _, channel = base_str.partition("@")
        return cls(name=name, channel=channel, architectures=architectures)


class BasesConfiguration(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Definition of build-on/run-on combinations."""

    build_on: list[Base]
    run_on: list[Base]


class Project(ModelConfigDefaults):
    """Internal-only project configuration."""

    # do not verify that `dirpath` is a valid existing directory; it's used externally as a dir
    # to load the config itself (so we're really do the validation there), and we want to support
    # the case of a missing directory (and still load a default config structure)
    dirpath: pathlib.Path
    config_provided: bool = False

    # this timestamp will be used in several places, even sent to Charmhub: needs to be UTC
    started_at: datetime.datetime


class Ignore(ModelConfigDefaults):
    """Definition of `analysis.ignore` configuration."""

    attributes: list[AttributeName] = []
    linters: list[LinterName] = []


class AnalysisConfig(ModelConfigDefaults, allow_population_by_field_name=True):
    """Definition of `analysis` configuration."""

    ignore: Ignore = Ignore()


class Links(ModelConfigDefaults):
    """Definition of `links` in metadata."""

    contact: pydantic.StrictStr | list[pydantic.StrictStr] | None
    documentation: pydantic.AnyHttpUrl | None
    issues: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    source: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    website: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None


class CharmcraftConfig(
    ModelConfigDefaults,
    validate_all=False,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Definition of charmcraft.yaml configuration."""

    # this needs to go before 'parts', as it used by the validator
    project: Project

    metadata_legacy: bool = False

    type: Literal["bundle", "charm"]
    name: pydantic.StrictStr | None
    summary: pydantic.StrictStr | None
    description: pydantic.StrictStr | None
    charmhub: CharmhubConfig = CharmhubConfig()
    parts: dict[str, Any] | None
    bases: list[BasesConfiguration] | None
    analysis: AnalysisConfig = AnalysisConfig()
    actions: JujuActions | None
    assumes: list[str | dict[str, list | dict]] | None
    containers: dict[str, Any] | None
    devices: dict[str, Any] | None
    title: pydantic.StrictStr | None
    extra_bindings: dict[str, Any] | None
    peers: dict[str, Any] | None
    provides: dict[str, Any] | None
    requires: dict[str, Any] | None
    resources: dict[str, Any] | None
    storage: dict[str, Any] | None
    subordinate: bool | None
    terms: list[str] | None
    links: Links | None
    config: JujuConfig | None

    @pydantic.validator("name", pre=True, always=True)
    def validate_name(cls, name, values):
        """Verify charm name is valid with exception when instantiated without YAML."""
        if values.get("type") == "charm" and not name:
            raise ValueError("needs value")

        return name

    @pydantic.validator("summary", pre=True, always=True)
    def validate_summary(cls, summary, values):
        """Verify charm summary is valid with exception when instantiated without YAML."""
        if values.get("type") == "charm" and not summary:
            raise ValueError("needs value")

        return summary

    @pydantic.validator("description", pre=True, always=True)
    def validate_description(cls, description, values):
        """Verify charm name is valid with exception when instantiated without YAML."""
        if values.get("type") == "charm" and not description:
            raise ValueError("needs value")

        return description

    @pydantic.validator("parts", pre=True, always=True)
    def validate_special_parts(cls, parts, values):
        """Verify parts type (craft-parts will re-validate the schemas for the plugins)."""
        if "type" not in values:
            # we need 'type' to be set in this validator; if not there it's an error in
            # the schema anyway, so the whole loading will fail (no need to raise an
            # extra error here, it gets confusing to the user)
            return None

        if parts is None:
            # no parts indicated, default to the type of package
            parts = {values["type"]: {}}

        if not isinstance(parts, dict):
            raise TypeError("value must be a dictionary")

        for name, part in parts.items():
            if not isinstance(part, dict):
                raise TypeError(f"part {name!r} must be a dictionary")
            # implicit plugin fixup
            if "plugin" not in part:
                part["plugin"] = name

        # if needed, create 'source' properties for special parts "charm" with plugin "charm".
        # and "bundle" with plugin "bundle", pointing to project's directory
        for name, part in parts.items():
            if name == "charm" and part["plugin"] == "charm":
                part.setdefault("source", str(values["project"].dirpath))

            if name == "bundle" and part["plugin"] == "bundle":
                part.setdefault("source", str(values["project"].dirpath))

        return parts

    @pydantic.validator("parts", each_item=True)
    def validate_each_part(cls, item):
        """Verify each part in the parts section. Craft-parts will re-validate them."""
        return parts.process_part_config(item)

    @pydantic.validator("bases", pre=True)
    def validate_bases_presence(cls, bases, values):
        """Forbid 'bases' in bundles.

        This is to avoid a possible confusion of expecting the bundle
        to be built in a specific environment
        """
        if values.get("type") == "bundle":
            raise ValueError("Field not allowed when type=bundle")
        return bases

    @pydantic.validator("actions", pre=True, always=True)
    def validate_actions(cls, actions, values):
        """Verify 'actions' in charms.

        Currently, actions will be passed through to the charms.
        And individual "actions.yaml" should not exists when actions
        is defined in charmcraft.yaml.
        """
        actions_yaml = parse_actions_yaml(values["project"].dirpath, allow_broken=True)
        if actions is None:
            return actions_yaml
        else:
            if actions_yaml is not None:
                raise ValueError(
                    "'actions.yaml' file not allowed when an 'actions' section is "
                    "defined in 'charmcraft.yaml'"
                )

            return JujuActions.parse_obj({"actions": actions})

    @pydantic.validator("config", pre=True, always=True)
    def validate_config(cls, config, values):
        """Verify 'actions' in charms.

        Currently, actions will be passed through to the charms.
        And individual "actions.yaml" should not exists when actions
        is defined in charmcraft.yaml.
        """
        config_yaml = parse_config_yaml(values["project"].dirpath, allow_broken=True)
        if config is None:
            return config_yaml
        else:
            if config_yaml is not None:
                raise ValueError(
                    "'config.yaml' file not allowed when an 'config' section is "
                    "defined in 'charmcraft.yaml'"
                )

            return JujuConfig.parse_obj(config)

    @classmethod
    def expand_short_form_bases(cls, bases: list[dict[str, Any]]) -> None:
        """Expand short-form base configuration into long-form in-place."""
        for index, base in enumerate(bases):
            # Skip if already long-form. Account for common typos in case user
            # intends to use long-form, but did so incorrectly (for better
            # error message handling).
            if "run-on" in base or "run_on" in base or "build-on" in base or "build_on" in base:
                continue

            try:
                converted_base = Base(**base)
            except pydantic.ValidationError as error:
                # Rewrite location to assist user.
                pydantic_errors = error.errors()
                for pydantic_error in pydantic_errors:
                    pydantic_error["loc"] = ("bases", index, pydantic_error["loc"][0])

                raise CraftError(format_pydantic_errors(pydantic_errors))

            base.clear()
            base["build-on"] = [converted_base.dict()]
            base["run-on"] = [converted_base.dict()]

    @classmethod
    def unmarshal(cls, obj: dict[str, Any], project: Project):
        """Unmarshal object with necessary translations and error handling.

        (1) Perform any necessary translations.

        (2) Standardize error reporting.

        :returns: valid CharmcraftConfig.

        :raises CraftError: On failure to unmarshal object.
        """
        try:
            # Expand short-form bases if only the bases is a valid list. If it
            # is not a valid list, parse_obj() will properly handle the error.
            if isinstance(obj.get("bases"), list):
                cls.expand_short_form_bases(obj["bases"])

            obj = apply_extensions(project.dirpath, obj)

            # Re-expand it in case extensions added short-form bases.
            if isinstance(obj.get("bases"), list):
                cls.expand_short_form_bases(obj["bases"])

            # If metadata.yaml exists, try merge it into config.
            if os.path.isfile(project.dirpath / const.METADATA_FILENAME):
                # metadata.yaml exists, so we can't specify metadata keys in charmcraft.yaml.
                for key in const.CHARM_METADATA_KEYS.union(const.METADATA_YAML_KEYS):
                    if key in obj:
                        raise CraftError(
                            f"Cannot specify '{key}' in charmcraft.yaml when "
                            f"'{const.METADATA_FILENAME}' exists"
                        )

                if obj.get("type") == "charm":
                    metadata_legacy = parse_charm_metadata_yaml(project.dirpath, allow_basic=True)

                    # need to copy 3 fields from metadata_legacy to charmcraft config
                    return cls.parse_obj(
                        {
                            "project": project,
                            "name": metadata_legacy.name,
                            "summary": metadata_legacy.summary,
                            "description": metadata_legacy.description,
                            "metadata-legacy": True,
                            **obj,
                        }
                    )
                elif obj.get("type") == "bundle":
                    # bundle may not have metadata.yaml.
                    # but if it does, it should have name and optional description
                    # metadata.yaml will be copied without validation if it exists
                    metadata_legacy = parse_bundle_metadata_yaml(project.dirpath)
                    return cls.parse_obj(
                        {
                            "project": project,
                            "name": metadata_legacy.name,
                            "description": metadata_legacy.description,
                            "metadata-legacy": True,
                            **obj,
                        }
                    )
                else:
                    # fallthrough for pydantic to handle
                    pass

            return cls.parse_obj({"project": project, **obj})
        except pydantic.ValidationError as error:
            raise CraftError(format_pydantic_errors(error.errors()))

    @classmethod
    def schema(cls, **kwargs) -> dict[str, Any]:
        """Perform any schema fixups required to hide internal details."""
        schema = super().schema(**kwargs)

        # The internal __root__ detail is leaked, overwrite it.
        schema["properties"]["parts"]["default"] = {}

        # Project is an internal detail, purge references.
        schema["definitions"].pop("Project", None)
        schema["properties"].pop("project", None)
        schema["required"].remove("project")
        return schema
