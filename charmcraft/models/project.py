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
from collections.abc import Iterable, Iterator
from typing import (
    Any,
    Literal,
    cast,
)

import craft_application.models
import pydantic
from craft_application import errors, models
from craft_application.util import get_host_architecture, safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from pydantic import dataclasses
from typing_extensions import Self, TypedDict

from charmcraft.const import (
    JUJU_ACTIONS_FILENAME,
    JUJU_CONFIG_FILENAME,
    METADATA_FILENAME,
    METADATA_YAML_KEYS,
)
from charmcraft.extensions import apply_extensions
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
    architectures: list[str]


LongFormBasesDict = TypedDict(
    "LongFormBasesDict", {"build-on": list[BaseDict], "run-on": list[BaseDict]}
)


class CharmPlatform(pydantic.ConstrainedStr):
    """The platform string for a charm file.

    This is to be generated in the form of the bases config in a charm file name.
    A charm's filename may look as follows:
        "{name}_{base0}_{base1}_{base...}.charm"
    where each base takes the form of:
        "{base_name}-{version}-{arch0}-{arch1}-{arch...}"

    For example, a charm called "test" that's built to run on Alma Linux 9 and Ubuntu 22.04
    on s390x and riscv64 platforms will have the name:
        test_almalinux-9-riscv64-s390x_ubuntu-22.04-riscv64-s390x.charm
    """

    min_length = 4
    strict = True
    strip_whitespace = True
    _host_arch = get_host_architecture()

    @classmethod
    def from_bases(cls: type[Self], bases: Iterable[charmcraft.Base]) -> Self:
        """Generate a platform name from a list of charm bases."""
        base_strings = []
        for base in bases:
            name = base.name
            version = base.channel
            architectures = "-".join(base.architectures)
            base_strings.append(f"{name}-{version}-{architectures}")
        return cls("_".join(base_strings))


@dataclasses.dataclass
class CharmBuildInfo(models.BuildInfo):
    """Information about a single build option, with charmcraft-specific info.

    With CharmBuildInfo, the build_for may also be the string "multi", meaning the charm
    is expected to run on multiple architectures.
    """

    platform: CharmPlatform

    build_for_bases: list[charmcraft.Base]
    """Charmcraft base to build for, including potentially multiple architectures."""
    bases_index: int
    """Index of the base configuration in charmcraft.yaml."""
    build_on_index: int
    """Index of this base configuration's build-on option."""

    @classmethod
    def from_build_on_run_on(
        cls: type[Self],
        build_on_base: charmcraft.Base,
        build_on_arch: str,
        run_on: list[charmcraft.Base],
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

        build_for = "-".join(sorted(all_architectures))

        platform = CharmPlatform.from_bases(run_on)

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
        cls: type[Self], *bases_configs: charmcraft.BasesConfiguration
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
    name: models.ProjectName | None
    title: models.ProjectTitle | None
    summary: models.SummaryStr | None
    description: str | None

    analysis: AnalysisConfig | None
    charmhub: CharmhubConfig | None
    parts: dict[str, dict[str, Any]] | None  # parts are handled by craft-parts

    # Default project properties that Charmcraft currently does not use. Types are set
    # to be Optional[None], preventing them from being used, but allow them to be used
    # by the application.
    version: None = None
    base: None = None
    license: None = None
    # These are inside the "links" child model.
    contact: None = None
    issues: None = None
    source_code: None = None

    # These private attributes are not part of the project model but are attached here
    # because Charmcraft uses this metadata.
    _started_at: datetime.datetime = pydantic.PrivateAttr(default_factory=datetime.datetime.utcnow)
    _valid: bool = pydantic.PrivateAttr(default=False)

    @property
    def started_at(self) -> datetime.datetime:
        """Get the time that Charmcraft started running."""
        return self._started_at

    @classmethod
    def unmarshal(cls, data: dict[str, Any]):
        """Create a Charmcraft project from a dictionary of data."""
        if cls is not CharmcraftProject:
            return cls.parse_obj(data)
        project_type = data.get("type")
        if project_type == "charm":
            return Charm.unmarshal(data)
        if project_type == "bundle":
            return Bundle.unmarshal(data)
        raise ValueError(f"field type cannot be {project_type!r}")

    @classmethod
    def from_yaml_data(cls, data: dict[str, Any], filepath: pathlib.Path) -> Self:
        """Instantiate this model from already-loaded YAML data.

        :param data: The dict of model properties.
        :param filepath: The filepath corresponding to ``data``, for error reporting.
        """
        data = apply_extensions(filepath.parent, data)

        try:
            return cls.unmarshal(data)
        except pydantic.ValidationError as err:
            cls.transform_pydantic_error(err)
            raise errors.CraftValidationError.from_pydantic(err, file_name=filepath.name) from None

    @classmethod
    def from_yaml_file(cls, path: pathlib.Path) -> Self:
        """Instantiate this model from a YAML file.

        For use with craft-application.
        """
        try:
            with path.open() as file:
                data = safe_yaml_load(file)
        except FileNotFoundError:
            raise CraftError(f"Could not find charmcraft.yaml at '{path}'")
        except OSError as exc:
            raise CraftError(
                f"Error parsing charmcraft.yaml at '{path}'", details=exc.strerror
            ) from exc

        if not isinstance(data, dict):
            raise errors.CraftValidationError(
                "Invalid 'charmcraft.yaml' file",
                details=f"File generated a {type(data)} object, expected a dictionary",
                resolution="Ensure 'charmcraft.yaml' is valid",
                reportable=False,
                docs_url="https://juju.is/docs/sdk/charmcraft-yaml",
            )

        project_dir = path.parent

        bundle_file = project_dir / "bundle.yaml"
        if data.get("type") == "bundle":
            if bundle_file.is_file():
                with bundle_file.open() as f:
                    data["bundle"] = safe_yaml_load(f)
            else:
                raise CraftError(f"Missing bundle.yaml file: {str(bundle_file)!r}")

        metadata_file = project_dir / METADATA_FILENAME
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
            metadata = parse_charm_metadata_yaml(project_dir, allow_basic=True)
            data.update(metadata.dict(include={"name", "summary", "description"}))

        config_file = project_dir / JUJU_CONFIG_FILENAME
        if config_file.is_file():
            if "config" in data:
                raise errors.CraftValidationError(
                    f"Cannot specify 'config' section in 'charmcraft.yaml' when {JUJU_CONFIG_FILENAME!r} exists",
                    resolution=f"Move all data from {JUJU_CONFIG_FILENAME!r} to the 'config' section in 'charmcraft.yaml'",
                )
            data["config"] = parse_config_yaml(project_dir, allow_broken=True)

        actions_file = project_dir / JUJU_ACTIONS_FILENAME
        if actions_file.is_file():
            if "actions" in data:
                raise errors.CraftValidationError(
                    f"Cannot specify 'actions' section in 'charmcraft.yaml' when {JUJU_ACTIONS_FILENAME!r} exists",
                    resolution=f"Move all data from {JUJU_ACTIONS_FILENAME!r} to the 'actions' section in 'charmcraft.yaml'",
                )
            data["actions"] = parse_actions_yaml(project_dir).actions

        try:
            project = cls.unmarshal(data)
        except pydantic.ValidationError as err:
            raise errors.CraftValidationError.from_pydantic(err, file_name=path.name)
        except ValueError as err:
            error_str = "\n".join(f"- {arg}" for arg in err.args)
            raise errors.CraftValidationError(
                f"Bad charmcraft.yaml content:\n{error_str}",
            )

        return project

    @pydantic.root_validator(pre=True, allow_reuse=True)
    def preprocess(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "type" not in values:
            raise ValueError("Project type must be declared in charmcraft.yaml.")

        return values

    @pydantic.validator("parts", pre=True, always=True, allow_reuse=True)
    def preprocess_parts(
        cls, parts: dict[str, dict[str, Any]] | None, values: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Preprocess parts object for a charm or bundle, creating an implicit part if needed."""
        if parts is not None and not isinstance(parts, dict):
            raise TypeError("'parts' in charmcraft.yaml must conform to the charmcraft.yaml spec.")
        if not parts:
            if "type" in values:
                parts = {values["type"]: {"plugin": values["type"]}}
            else:
                parts = {}
        for name, part in parts.items():
            if not isinstance(part, dict):
                raise TypeError(f"part {name!r} must be a dictionary.")
            # implicit plugin fixup
            if "plugin" not in part:
                part["plugin"] = name

        for name, part in parts.items():
            if name == "charm" and part["plugin"] == "charm":
                part.setdefault("source", ".")

            if name == "bundle" and part["plugin"] == "bundle":
                part.setdefault("source", ".")
        return parts

    @pydantic.validator("parts", each_item=True, allow_reuse=True)
    def validate_each_part(cls, item):
        """Verify each part in the parts section. Craft-parts will re-validate them."""
        return process_part_config(item)


craft_application.models.Project.register(CharmcraftProject)


class Charm(CharmcraftProject):
    """Model for defining a charm."""

    type: Literal["charm"]
    name: models.ProjectName
    summary: models.SummaryStr
    description: str

    # This is defined this way because using conlist makes mypy sad and using
    # a ConstrainedList child class has pydontic issues. This appears to be
    # solved with Pydantic 2.
    bases: list[BasesConfiguration] = pydantic.Field(min_items=1)

    parts: dict[str, dict[str, Any]] = {"charm": {"plugin": "charm", "source": "."}}

    actions: dict[str, Any] | None
    assumes: list[str | dict[str, list | dict]] | None
    containers: dict[str, Any] | None
    devices: dict[str, Any] | None
    extra_bindings: dict[str, Any] | None
    peers: dict[str, Any] | None
    provides: dict[str, Any] | None
    requires: dict[str, Any] | None
    resources: dict[str, Any] | None
    storage: dict[str, Any] | None
    subordinate: bool | None
    terms: list[str] | None
    links: Links | None
    config: dict[str, Any] | None

    @pydantic.validator("bases", pre=True, each_item=True, allow_reuse=True)
    def expand_base(cls, base: BaseDict | LongFormBasesDict) -> LongFormBasesDict:
        """Expand short-form bases into long-form bases."""
        if "name" not in base:  # Assume long-form base already.
            return cast(LongFormBasesDict, base)
        return cast(LongFormBasesDict, {"build-on": [base], "run-on": [base]})

    def get_build_plan(self) -> list[models.BuildInfo]:
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
        return list(CharmBuildInfo.gen_from_bases_configurations(*self.bases))


class Bundle(CharmcraftProject):
    """Model for defining a bundle."""

    type: Literal["bundle"]
    bundle: dict[str, Any] = {}
    name: models.ProjectName | None = None
    title: models.ProjectTitle | None
    summary: models.SummaryStr | None
    description: pydantic.StrictStr | None
    charmhub: CharmhubConfig = CharmhubConfig()

    @pydantic.root_validator(pre=True)
    def preprocess_bundle(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "name" not in values:
            values["name"] = values.get("bundle", {}).get("name")

        return values
