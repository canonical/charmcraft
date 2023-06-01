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

"""Charmcraft configuration pydantic model."""

import datetime
import pathlib
import os
import re
import keyword
from typing import Optional, List, Dict, Any

import pydantic

from craft_cli import CraftError
from charmcraft.parts import process_part_config
from charmcraft.utils import get_host_architecture
from charmcraft.format import format_pydantic_errors


class ModelConfigDefaults(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Define Charmcraft's defaults for the BaseModel configuration."""


class CustomStrictStr(pydantic.StrictStr):
    """Generic class to create custom strict strings validated by pydantic."""

    @classmethod
    def __get_validators__(cls):
        """Yield the relevant validators."""
        yield from super().__get_validators__()
        yield cls.custom_validate


class RelativePath(CustomStrictStr):
    """Constrained string which must be a relative path."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate relative path.

        Check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        config is independent of the platform where charmcraft is running.
        """
        if not value:
            raise ValueError(f"{value!r} must be a valid relative path (cannot be empty)")

        if value[0] == "/":
            raise ValueError(f"{value!r} must be a valid relative path (cannot start with '/')")

        return value


class AttributeName(CustomStrictStr):
    """Constrained string that must match the name of an attribute from linters.CHECKERS."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate attribute name."""
        from charmcraft import linters  # import here to avoid cyclic imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.attribute
        ]
        if value not in valid_names:
            raise ValueError(f"Bad attribute name {value!r}")
        return value


class LinterName(CustomStrictStr):
    """Constrained string that must match the name of a linter from linters.CHECKERS."""

    @classmethod
    def custom_validate(cls, value: str) -> str:
        """Validate attribute name."""
        from charmcraft import linters  # import here to avoid cyclic imports

        valid_names = [
            checker.name
            for checker in linters.CHECKERS
            if checker.check_type == linters.CheckType.lint
        ]
        if value not in valid_names:
            raise ValueError(f"Bad lint name {value!r}")
        return value


class CharmhubConfig(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Definition of Charmhub endpoint configuration."""

    api_url: pydantic.HttpUrl = "https://api.charmhub.io"
    storage_url: pydantic.HttpUrl = "https://storage.snapcraftcontent.com"
    registry_url: pydantic.HttpUrl = "https://registry.jujucharms.com"


class Base(ModelConfigDefaults):
    """Represents a base."""

    name: pydantic.StrictStr
    channel: pydantic.StrictStr
    architectures: List[pydantic.StrictStr] = [get_host_architecture()]


class BasesConfiguration(
    ModelConfigDefaults,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Definition of build-on/run-on combinations."""

    build_on: List[Base]
    run_on: List[Base]


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

    attributes: List[AttributeName] = []
    linters: List[LinterName] = []


class AnalysisConfig(ModelConfigDefaults, allow_population_by_field_name=True):
    """Definition of `analysis` configuration."""

    ignore: Ignore = Ignore()


class Config(ModelConfigDefaults, validate_all=False):
    """Definition of charmcraft.yaml configuration."""

    # this needs to go before 'parts', as it used by the validator
    project: Project

    type: str
    charmhub: CharmhubConfig = CharmhubConfig()
    parts: Optional[Dict[str, Any]]
    bases: Optional[List[BasesConfiguration]]
    analysis: AnalysisConfig = AnalysisConfig()
    actions: Optional[Dict[str, Any]]

    @pydantic.validator("type")
    def validate_charm_type(cls, charm_type):
        """Verify charm type is valid with exception when instantiated without YAML."""
        if charm_type not in ["bundle", "charm"]:
            raise ValueError("must be either 'charm' or 'bundle'")
        return charm_type

    @pydantic.validator("parts", pre=True, always=True)
    def validate_special_parts(cls, parts, values):
        """Verify parts type (craft-parts will re-validate the schemas for the plugins)."""
        if "type" not in values:
            # we need 'type' to be set in this validator; if not there it's an error in
            # the schema anyway, so the whole loading will fail (no need to raise an
            # extra error here, it gets confusing to the user)
            return

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
    def validate_each_part(cls, item, values):
        """Verify each part in the parts section. Craft-parts will re-validate them."""
        completed_item = process_part_config(item)
        return completed_item

    @pydantic.validator("bases", pre=True)
    def validate_bases_presence(cls, bases, values):
        """Forbid 'bases' in bundles.

        This is to avoid a possible confusion of expecting the bundle
        to be built in a specific environment
        """
        if values.get("type") == "bundle":
            raise ValueError("Field not allowed when type=bundle")
        return bases

    @pydantic.validator("actions", pre=True)
    def validate_actions(cls, actions, values):
        """Verify 'actions' in charms.

        Currently, actions will be passed through to the charms.
        And individual "actions.yaml" should not exists when actions
        is defined in charmcraft.yaml.
        """
        if actions is None:
            return None

        actions_yaml_file_path = values["project"].dirpath / "actions.yaml"
        if os.path.isfile(actions_yaml_file_path):
            raise ValueError(
                "'actions.yaml' file not allowed when an 'actions' section is "
                "defined in 'charmcraft.yaml'"
            )

        # https://juju.is/docs/sdk/actions
        action_name_regex = re.compile(r"^[a-zA-Z_][a-zA-Z0-9-_]*$")
        for action in actions.keys():
            if keyword.iskeyword(action):
                raise ValueError(
                    f"'{action}' is a reserved keyword and cannot be used as an action name"
                )
            if action_name_regex.match(action) is None:
                raise ValueError(f"'{action}' is not a valid action name")

        return actions

    @classmethod
    def expand_short_form_bases(cls, bases: List[Dict[str, Any]]) -> None:
        """Expand short-form base configuration into long-form in-place."""
        for index, base in enumerate(bases):
            # Skip if already long-form. Account for common typos in case user
            # intends to use long-form, but did so incorrectly (for better
            # error message handling).
            if "run-on" in base or "run_on" in base or "build-on" in base or "build_on" in base:
                continue

            try:
                converted_base = Base(**base)
            except pydantic.error_wrappers.ValidationError as error:
                # Rewrite location to assist user.
                pydantic_errors = error.errors()
                for pydantic_error in pydantic_errors:
                    pydantic_error["loc"] = ("bases", index, pydantic_error["loc"][0])

                raise CraftError(format_pydantic_errors(pydantic_errors))

            base.clear()
            base["build-on"] = [converted_base.dict()]
            base["run-on"] = [converted_base.dict()]

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any], project: Project):
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

            return cls.parse_obj({"project": project, **obj})
        except pydantic.error_wrappers.ValidationError as error:
            raise CraftError(format_pydantic_errors(error.errors()))

    @classmethod
    def schema(cls, **kwargs) -> Dict[str, Any]:
        """Perform any schema fixups required to hide internal details."""
        schema = super().schema(**kwargs)

        # The internal __root__ detail is leaked, overwrite it.
        schema["properties"]["parts"]["default"] = {}

        # Project is an internal detail, purge references.
        schema["definitions"].pop("Project", None)
        schema["properties"].pop("project", None)
        schema["required"].remove("project")
        return schema
