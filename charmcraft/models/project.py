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
"""Project-related models for Charmcraft."""
import abc
import datetime
import pathlib
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Type,
    TypedDict,
    Union,
)

import pydantic
from craft_application import errors, models
from craft_application.util import safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from pydantic import dataclasses
from typing_extensions import Self

from charmcraft.const import (
    JUJU_ACTIONS_FILENAME,
    JUJU_CONFIG_FILENAME,
    METADATA_FILENAME,
    METADATA_YAML_KEYS,
)
from charmcraft.metafiles.actions import parse_actions_yaml
from charmcraft.metafiles.config import parse_config_yaml
from charmcraft.metafiles.metadata import parse_charm_metadata_yaml
from charmcraft.models import charmcraft
from charmcraft.models.charmcraft import (
    AnalysisConfig,
    BasesConfiguration,
    CharmhubConfig,
    Links,
)
from charmcraft.parts import process_part_config


class BaseDict(TypedDict, total=False):
    """TypedDict that describes only one base.

    This is equivalent to the short form base definition.
    """

    name: str
    channel: str
    architectures: List[str]


LongFormBasesDict = TypedDict(
    "LongFormBasesDict", {"build-on": List[BaseDict], "run-on": List[BaseDict]}
)


@dataclasses.dataclass
class CharmBuildInfo(models.BuildInfo):
    """Information about a single build option, with charmcraft-specific info.

    With CharmBuildInfo, the build_for may also be the string "multi", meaning the charm
    is expected to run on multiple architectures.
    """

    build_for_bases: List[charmcraft.Base]
    """Charmcraft base to build for, including potentially multiple architectures."""
    bases_index: int
    """Index of the base configuration in charmcraft.yaml."""
    build_on_index: int
    """Index of this base configuration's build-on option."""

    @classmethod
    def from_build_on_run_on(
        cls: Type[Self],
        build_on_base: charmcraft.Base,
        build_on_arch: str,
        run_on: List[charmcraft.Base],
        *,
        bases_index: int,
        build_on_index: int,
    ) -> Self:
        """Create a single CharmBuildInfo from a build_on base and run_on bases.

        :param build_on_base: A Base object defining a base on which to build
        :param build_on_arch: The architecture on which to run the build (e.g. "amd64")
        :param run_on: A list of bases which this charm should run on after the build.
        :param bases_index: The index of the BasesConfiguration
        :param build_on_index: Which build-on value from the BasesConfiguration to use
        """
        base = bases.BaseName(name=build_on_base.name, version=build_on_base.channel)

        all_architectures = set()
        for run_on_base in run_on:
            all_architectures.update(run_on_base.architectures)

        build_for = all_architectures.pop() if len(all_architectures) == 1 else "multi"

        platform = f"{base.name}-{base.version}-{build_for}"

        return cls(
            platform=platform,
            build_on=build_on_arch,
            build_for=build_for,
            base=base,
            build_for_bases=run_on,
            bases_index=bases_index,
            build_on_index=build_on_index,
        )

    @classmethod
    def gen_from_bases_configurations(
        cls: Type[Self], *bases_configs: charmcraft.BasesConfiguration
    ) -> Iterator[Self]:
        """Generate CharmBuildInfo objects from a BasesConfiguration object.

        :param bases_config: One or more BasesConfiguration objects from which to generate
            CharmBuildInfo objects.
        :returns: A list of CharmBuildInfo objects from this BasesConfiguration.
        """
        for bases_index, bases_config in enumerate(bases_configs):
            for build_on_index, build_on_base in enumerate(bases_config.build_on):
                for build_on_arch in build_on_base.architectures:
                    yield cls.from_build_on_run_on(
                        build_on_base,
                        build_on_arch,
                        bases_config.run_on,
                        bases_index=bases_index,
                        build_on_index=build_on_index,
                    )


class CharmcraftProject(models.CraftBaseModel, metaclass=abc.ABCMeta):
    """A craft-application compatible version of a Charmcraft project.

    This is a Project definition for charmcraft commands that are run through
    craft-application rather than the legacy charmcraft entrypoint. Eventually
    it will be the only form of the project.

    This inherits from CraftBaseModel rather than from the base craft-application Project
    in order to preserve field order. It's registered as a virtual child class below.
    """

    type: Literal["charm", "bundle"]
    name: Optional[models.ProjectName]
    title: Optional[models.ProjectTitle]
    summary: Optional[models.SummaryStr]
    description: Optional[str]

    analysis: Optional[AnalysisConfig]
    charmhub: Optional[CharmhubConfig]
    parts: Optional[Dict[str, Dict[str, Any]]]  # parts are handled by craft-parts

    # Default project properties that Charmcraft currently does not use. Types are set
    # to be Optional[None], preventing them from being used, but allow them to be used
    # by the application.
    version: Optional[None] = None
    base: Optional[None] = None
    license: Optional[None] = None
    # These are inside the "links" child model.
    contact: Optional[None] = None
    issues: Optional[None] = None
    source_code: Optional[None] = None

    # These private attributes are not part of the project model but are attached here
    # because Charmcraft uses this metadata.
    _started_at: datetime.datetime = pydantic.PrivateAttr(default_factory=datetime.datetime.utcnow)

    @property
    def started_at(self) -> datetime.datetime:
        return self._started_at

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> Self:
        """Create a Charmcraft project from a dictionary of data."""
        project_type = data.get("type")
        if project_type == "charm":
            return Charm.parse_obj(data)
        if project_type == "bundle":
            return Bundle.parse_obj(data)
        raise ValueError(f"field type cannot be {project_type!r}")

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> Self:
        """Instantiate this model from a YAML file.

        For use with craft-application.
        """
        if not path.exists():
            raise CraftError(f"Could not find charmcraft.yaml at {path}")

        with path.open() as file:
            data = safe_yaml_load(file)

        if not isinstance(data, dict):
            raise errors.CraftValidationError(
                "Invalid 'charmcraft.yaml' file",
                details=f"File generated a {type(data)} object, expected a dictionary",
                resolution="Ensure 'charmcraft.yaml' is valid",
                reportable=False,
                docs_url="https://juju.is/docs/sdk/charmcraft-yaml",
            )

        charm_dir = path.parent

        metadata_file = charm_dir / METADATA_FILENAME
        if metadata_file.is_file():
            # metadata.yaml exists, so we can't specify metadata keys in charmcraft.yaml.
            overlap_keys = METADATA_YAML_KEYS.intersection(data.keys())
            if overlap_keys:
                raise errors.CraftValidationError(
                    f"Cannot specify metadata keys in 'charmcraft.yaml' when "
                    f"{METADATA_FILENAME!r} exists",
                    details=f"Invalid keys: {sorted(overlap_keys)}",
                    resolution=f"Migrate all keys from {METADATA_FILENAME!r} to 'charmcraft.yaml'",
                )
            metadata = parse_charm_metadata_yaml(charm_dir, allow_basic=True)
            data.update(metadata.dict(include={"name", "summary", "description"}))

        config_file = charm_dir / JUJU_CONFIG_FILENAME
        if config_file.is_file():
            if "config" in data:
                raise errors.CraftValidationError(
                    f"Cannot specify 'config' section in 'charmcraft.yaml' when {JUJU_CONFIG_FILENAME!r} exists",
                    resolution=f"Move all data from {JUJU_CONFIG_FILENAME!r} to the 'config' section in 'charmcraft.yaml'",
                )
            data["config"] = parse_config_yaml(charm_dir, allow_broken=True)

        actions_file = charm_dir / JUJU_ACTIONS_FILENAME
        if actions_file.is_file():
            if "actions" in data:
                raise errors.CraftValidationError(
                    f"Cannot specify 'actions' section in 'charmcraft.yaml' when {JUJU_ACTIONS_FILENAME!r} exists",
                    resolution=f"Move all data from {JUJU_ACTIONS_FILENAME!r} to the 'actions' section in 'charmcraft.yaml'",
                )
            data["actions"] = parse_actions_yaml(charm_dir, allow_broken=True)

        try:
            project = cls.unmarshal(data)
        except pydantic.ValidationError as err:
            raise errors.CraftValidationError.from_pydantic(err, file_name=path.name) from None
        except ValueError as err:
            error_str = "\n".join(f"- {arg}" for arg in err.args)
            raise errors.CraftValidationError(
                f"Bad charmcraft.yaml content:\n{error_str}",
                resolution="Set the 'type' field in 'charmcraft.yaml' to either 'charm' or 'bundle'",
                reportable=False,
            )

        return project

    @pydantic.root_validator(pre=True)
    def preprocess_values(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "type" not in values:
            raise ValueError("Project type must be declared in charmcraft.yaml.")

        return values

    @pydantic.validator("parts", pre=True)
    def preprocess_parts(
        cls, parts: Optional[Dict[str, Dict[str, Any]]], values: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Preprocess parts object for a charm or bundle, creating an implicit part if needed."""
        if not isinstance(parts, dict):
            raise TypeError("'parts' in charmcraft.yaml must conform to the charmcraft.yaml spec.")
        default_parts = {values["type"]: {"plugin": values["type"]}}
        if not parts:
            parts = default_parts
        for name, part in parts.items():
            if not isinstance(part, dict):
                raise TypeError(f"part {name!r} must be a dictionary.")
            # implicit plugin fixup
            if "plugin" not in part:
                part["plugin"] = name

        # TODO: Figure out how to implicitly set the source path for the part.
        # if needed, create 'source' properties for special parts "charm" with plugin "charm".
        # and "bundle" with plugin "bundle", pointing to project's directory
        for name, part in parts.items():
            if name == "charm" and part["plugin"] == "charm":
                part.setdefault("source", ".")

            if name == "bundle" and part["plugin"] == "bundle":
                part.setdefault("source", ".")
        return parts

    @pydantic.validator("parts", each_item=True)
    def validate_each_part(cls, item, values):
        """Verify each part in the parts section. Craft-parts will re-validate them."""
        return process_part_config(item)

    #
    # @pydantic.validator("config", pre=True, always=True)
    # def validate_config(cls, config, values):
    #     """Verify 'actions' in charms.
    #
    #     Currently, actions will be passed through to the charms.
    #     And individual "actions.yaml" should not exists when actions
    #     is defined in charmcraft.yaml.
    #     """
    #     if config is None:
    #         if config_yaml is not None:
    #             raise ValueError(
    #                 "'config.yaml' file not allowed when an 'config' section is "
    #                 "defined in 'charmcraft.yaml'"
    #


class Charm(CharmcraftProject):
    """Model for defining a charm."""

    type: Literal["charm"]
    name: models.ProjectName
    summary: models.SummaryStr
    description: str

    bases: pydantic.conlist(BasesConfiguration, min_items=1)

    parts: Dict[str, Dict[str, Any]] = {"charm": {"plugin": "charm", "source": "."}}

    actions: Optional[Dict[str, Any]]  # TODO: Make this a valid actions.yaml
    assumes: Optional[List[Union[str, Dict[str, Union[List, Dict]]]]]
    containers: Optional[Dict[str, Any]]
    devices: Optional[Dict[str, Any]]
    extra_bindings: Optional[Dict[str, Any]]
    peers: Optional[Dict[str, Any]]
    provides: Optional[Dict[str, Any]]
    requires: Optional[Dict[str, Any]]
    resources: Optional[Dict[str, Any]]
    storage: Optional[Dict[str, Any]]
    subordinate: Optional[bool]
    terms: Optional[List[str]]
    links: Optional[Links]
    # TODO: Make this better
    config: Optional[Dict[str, Any]]

    # def marshal(self) -> Dict[str, Union[str, List[str], Dict[str, Any]]]:

    @pydantic.validator("bases", pre=True, each_item=True)
    def expand_base(cls, base: Union[BaseDict, LongFormBasesDict]) -> LongFormBasesDict:
        """Expand short-form bases into long-form bases."""
        if "name" not in base:  # Assume long-form base already.
            return base
        return {"build-on": [base], "run-on": [base]}

    # @pydantic.root_validator(pre=True)
    # def preprocess_charm(cls, values: Dict[str, Any]) -> Dict[str, Any]:
    #     """Preprocess inferred values specific to charms before attribute validation."""
    #

    def get_build_plan(self) -> List[models.BuildInfo]:
        """Get build bases for this charm.

        This method provides a flattened version of every way to build the charm, unfiltered.

        Example 1: a simple charm:
            bases:
              - name: ubuntu
                channel: 24.04
        This gets expanded to a standard long-form:
            bases:
              - build-on:
                  - name: ubuntu
                    channel: "24.04"
                run-on:
                  - name: ubuntu
                    channel: "24.04"
        Presuming charmcraft is run on riscv64 (if architectures are not specified charmcraft will
        use the host architecture as the only architecture), it will output a list containing the
        following single BuildInfo object:
            CharmBuildInfo(
                build_on="riscv64",
                build_for="riscv64",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_base=BaseName(name="ubuntu", channel="24.04"),
                bases_index=0,
                build_on_index=0
            )

        Example 2: a more complex set of bases:
            bases:
              - build-on:
                  - name: ubuntu
                    channel: "24.04"
                    architectures: ["amd64", "riscv64"]
                  - name: ubuntu
                    channel: "22.04"
                    architectures: ["arm64"]
                run-on:
                  - name: ubuntu
                    channel: "22.04"
                    architectures: ["amd64", "arm64"]
                  - name: ubuntu
                    channel: "24.04"
                    architectures: ["amd64", "arm64", "riscv64"]
        This will result in the following builds in the plan:
        [
            CharmBuildInfo(
                build_on="amd64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=0
            ),
            CharmBuildInfo(
                build_on="riscv64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="24.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=0
            ),
            CharmBuildInfo(
                build_on="arm64",
                build_for="multi",
                base=BaseName(name="ubuntu", channel="22.04"),
                build_for_bases=[
                    Base(name="ubuntu", channel="22.04", architectures=["amd64", "arm64"]),
                    Base(name="ubuntu", channel="24.04", architectures=["amd64", "arm64", "riscv64"])
                ]
                bases_index=0,
                build_on_index=1
            ),
        ]

        Here the string "multi" defines a destination platform that has multiple architectures.
        """
        if not self.bases:
            raise CraftError("Cannot create build plan because no bases were provided.")

        return list(CharmBuildInfo.gen_from_bases_configurations(*self.bases))


class Bundle(CharmcraftProject):
    """Model for defining a bundle."""

    type: Literal["bundle"]
    name: Optional[models.ProjectName]
    title: Optional[models.ProjectTitle]
    summary: Optional[pydantic.StrictStr]
    description: Optional[pydantic.StrictStr]
    charmhub: CharmhubConfig = CharmhubConfig()

    @pydantic.root_validator(pre=True)
    def preprocess_bundle(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess inferred values specific to bundles before attribute validation."""
        if values.get("type") != "bundle":
            return values

        return values

    def get_build_plan(self) -> List[CharmBuildInfo]:
        # TODO!!! Pretty sure this is a no-op though?
        raise NotImplementedError
