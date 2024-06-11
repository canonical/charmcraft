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
"""Project-related models for Charmcraft."""
import abc
import datetime
import pathlib
import re
from collections.abc import Iterable, Iterator
from typing import (
    Any,
    Literal,
    cast,
)

import pydantic
from craft_application import errors, models
from craft_application.util import get_host_architecture, safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from pydantic import dataclasses
from typing_extensions import Self, TypedDict

from charmcraft import const, preprocess, utils
from charmcraft.const import (
    BaseStr,
    BuildBaseStr,
    CharmArch,
)
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


class CharmcraftSummaryStr(models.SummaryStr):
    """A brief summary of this charm or bundle. Ideally, this should fit into one line."""

    # Maximum length was set to 200 characters because the 78 character maximum
    # inherited from craft-application is too restrictive, as several hundred charms
    # already exceed this maximum.
    # Eventually this limit will be reduced, ideally to 78 characters, though that may
    # never happen entirely. Reductions will only occur on major releases.
    # https://github.com/canonical/charmcraft/issues/1598
    max_length = 200


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


class Platform(models.CraftBaseModel):
    """Project platform definition."""

    build_on: list[CharmArch] = pydantic.Field(min_items=1)
    build_for: list[CharmArch | Literal["all"]] = pydantic.Field(min_items=1, max_items=1)

    @pydantic.validator("build_on", "build_for", pre=True)
    def _listify_architectures(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [value]
        return value


class CharmLib(models.CraftBaseModel):
    """A Charm library dependency for this charm."""

    lib: str = pydantic.Field(
        title="Library Path (e.g. my-charm.my_library)",
        regex=r"[a-z][a-z0-9_-]+\.[a-z][a-z0-9_]+",
    )
    version: str = pydantic.Field(
        title="Version filter for the charm. Either an API version or a specific [api].[patch].",
        regex=r"[0-9]+(\.[0-9]+)?",
    )

    @pydantic.validator("lib", pre=True)
    def _validate_name(cls, value: str) -> str:
        """Validate the lib field, providing a useful error message on failure."""
        charm_name, _, lib_name = str(value).partition(".")
        if not charm_name or not lib_name:
            raise ValueError(
                f"Library name invalid. Expected '[charm_name].[lib_name]', got {value!r}"
            )
        # Accept python-importable charm names, but convert them to store-accepted names.
        if "_" in charm_name:
            charm_name = charm_name.replace("_", "-")
        if not re.fullmatch("[a-z0-9_-]+", charm_name):
            raise ValueError(
                f"Invalid charm name for lib {value!r}. Value {charm_name!r} is invalid."
            )
        if not re.fullmatch("[a-z0-9_]+", lib_name):
            raise ValueError(
                f"Library name {lib_name!r} is invalid. Library names must be valid Python module names."
            )
        return str(value)

    @pydantic.validator("version", pre=True)
    def _validate_api_version(cls, value: str) -> str:
        """Validate the API version field, providing a useful error message on failure."""
        api, *_ = str(value).partition(".")
        try:
            int(api)
        except ValueError:
            raise ValueError(f"API version not valid. Expected an integer, got {api!r}") from None
        return str(value)

    @pydantic.validator("version", pre=True)
    def _validate_patch_version(cls, value: str) -> str:
        """Validate the optional patch version, providing a useful error message."""
        api, separator, patch = value.partition(".")
        if not separator:
            return value
        try:
            int(patch)
        except ValueError:
            raise ValueError(
                f"Patch version not valid. Expected an integer, got {patch!r}"
            ) from None
        return value

    @property
    def api_version(self) -> int:
        """The API version needed for this library."""
        return int(self.version.partition(".")[0])

    @property
    def patch_version(self) -> int | None:
        """The patch version needed for this library, or None if no patch version is specified."""
        api, _, patch = self.version.partition(".")
        if not patch:
            return None
        return int(patch)


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


class CharmcraftBuildPlanner(models.BuildPlanner):
    """Build planner for Charmcraft."""

    type: str = ""
    bases: list[BasesConfiguration] = pydantic.Field(default_factory=list)
    base: str | None = None
    build_base: str | None = None
    platforms: dict[str, Platform | None] | None = None

    @pydantic.validator("bases", pre=True, each_item=True, allow_reuse=True)
    def expand_base(cls, base: BaseDict | LongFormBasesDict) -> LongFormBasesDict:
        """Expand short-form bases into long-form bases."""
        if "name" not in base:  # Assume long-form base already.
            return cast(LongFormBasesDict, base)
        return cast(LongFormBasesDict, {"build-on": [base], "run-on": [base]})

    def get_build_plan(self) -> list[models.BuildInfo]:
        """Get build bases for this charm.

        This method provides a flattened version of every way to build the charm, unfiltered.

        If a charm uses the older "bases" model, it defers to
        `CharmBuildInfo.gen_from_bases_configurations'. Otherwise, it generates the BuildInfo
        as expected with platforms.
        """
        if self.type == "bundle":
            # A bundle can build anywhere, so just present the current system.
            current_arch = utils.get_host_architecture()
            current_base = utils.get_os_platform()
            return [
                models.BuildInfo(
                    platform=current_arch,
                    build_on=current_arch,
                    build_for=current_arch,
                    base=bases.BaseName(name=current_base.system, version=current_base.release),
                )
            ]
        if not self.base:
            return list(CharmBuildInfo.gen_from_bases_configurations(*self.bases))

        build_base = self.build_base or self.base
        base_name, _, base_version = build_base.partition("@")
        base = bases.BaseName(name=base_name, version=base_version)

        if self.platforms is None:
            raise CraftError("Must define at least one platform.")
        build_infos = []
        for platform_name, platform in self.platforms.items():
            if platform is None:
                if platform_name not in const.SUPPORTED_ARCHITECTURES:
                    raise CraftError(
                        f"Invalid platform {platform_name}.",
                        details="A platform name must either be a valid architecture name or the "
                        "platform must specify one or more build-on and build-for architectures.",
                    )
                build_infos.append(
                    models.BuildInfo(
                        platform_name, build_on=platform_name, build_for=platform_name, base=base
                    )
                )
            else:
                for build_on in platform.build_on:
                    build_infos.extend(
                        [
                            models.BuildInfo(
                                platform_name,
                                build_on=str(build_on),
                                build_for=str(build_for),
                                base=base,
                            )
                            for build_for in platform.build_for
                        ]
                    )
        return build_infos


class CharmcraftProject(models.Project, metaclass=abc.ABCMeta):
    """A craft-application compatible version of a Charmcraft project.

    This is a Project definition for charmcraft commands that are run through
    craft-application rather than the legacy charmcraft entrypoint. Eventually
    it will be the only form of the project.

    This inherits from CraftBaseModel rather than from the base craft-application Project
    in order to preserve field order. It's registered as a virtual child class below.
    """

    type: Literal["charm", "bundle"]
    title: models.ProjectTitle | None
    summary: CharmcraftSummaryStr | None
    description: str | None

    analysis: AnalysisConfig | None
    charmhub: CharmhubConfig | None
    parts: dict[str, dict[str, Any]] = pydantic.Field(default_factory=dict)

    # Default project properties that Charmcraft currently does not use. Types are set
    # to be Optional[None], preventing them from being used, but allow them to be used
    # by the application.
    version: Literal["unversioned"] = "unversioned"  # type: ignore[assignment]
    license: None = None
    # These are inside the "links" child model.
    contact: None = None
    issues: None = None
    source_code: None = None
    charm_libs: list[CharmLib] = pydantic.Field(
        default_factory=list, title="List of libraries to use for this charm"
    )

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
            if "bases" in data:
                return BasesCharm.unmarshal(data)
            return PlatformCharm.unmarshal(data)
        if project_type == "bundle":
            return Bundle.unmarshal(data)
        raise ValueError(f"field type cannot be {project_type!r}")

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

        preprocess.add_default_parts(data)
        preprocess.add_bundle_snippet(project_dir, data)
        preprocess.add_metadata(project_dir, data)
        preprocess.add_config(project_dir, data)
        preprocess.add_actions(project_dir, data)

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


class BasesCharm(CharmcraftProject):
    """Model for defining a charm."""

    type: Literal["charm"]
    name: models.ProjectName
    summary: CharmcraftSummaryStr
    description: str

    # This is defined this way because using conlist makes mypy sad and using
    # a ConstrainedList child class has pydontic issues. This appears to be
    # solved with Pydantic 2.
    bases: list[BasesConfiguration] = pydantic.Field(min_items=1)

    base: None = None

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
    def _validate_base(cls, base: BaseDict | LongFormBasesDict) -> LongFormBasesDict:
        """Expand short-form bases into long-form bases."""
        if "name" in base:  # Convert short form to long form
            base = cast(LongFormBasesDict, {"build-on": [base], "run-on": [base]})
        else:  # Cast to long form since we know it is one.
            base = cast(LongFormBasesDict, base)

        # Ensure we're only allowing legacy bases.
        for build_base in base["build-on"]:
            if not cls._check_base_is_legacy(build_base):
                raise ValueError(f"Base requires 'platforms' definition: {build_base}")
        for run_base in base["run-on"]:
            if not cls._check_base_is_legacy(run_base):
                raise ValueError(f"Base requires 'platforms' definition: {run_base}")

        return base

    @staticmethod
    def _check_base_is_legacy(base: BaseDict) -> bool:
        """Check that the given base is a legacy base, usable with 'bases'."""
        # This pyright ignore can go away once we're on Python minimum version 3.11.
        # At that point we can mark items as required or not required.
        # https://docs.python.org/3/library/typing.html#typing.Required
        if (
            base["name"] == "ubuntu"  # pyright: ignore[reportTypedDictNotRequiredAccess]
            and base["channel"] < "24.04"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        ):
            return True
        if base in ({"name": "centos", "channel": "7"}, {"name": "almalinux", "channel": "9"}):
            return True
        return False


class PlatformCharm(CharmcraftProject):
    """Model for defining a charm using Platforms."""

    type: Literal["charm"]
    name: models.ProjectName
    summary: CharmcraftSummaryStr
    description: str

    base: BaseStr
    build_base: BuildBaseStr | None = None
    platforms: dict[str, Platform | None]

    parts: dict[str, dict[str, Any]]  # craft-parts parts

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

    @staticmethod
    def _check_base_is_legacy(base: BaseDict) -> bool:
        """Check that the given base is a legacy base, usable with 'bases'."""
        # This pyright ignore can go away once we're on Python minimum version 3.11.
        # At that point we can mark items as required or not required.
        # https://docs.python.org/3/library/typing.html#typing.Required
        if (
            base["name"] == "ubuntu"  # pyright: ignore[reportTypedDictNotRequiredAccess]
            and base["channel"] < "24.04"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        ):
            return True
        if base in ({"name": "centos", "channel": "7"}, {"name": "almalinux", "channel": "9"}):
            return True
        return False

    @pydantic.validator("build_base", always=True)
    def _validate_dev_base_needs_build_base(
        cls, build_base: str | None, values: dict[str, Any]
    ) -> str | None:
        if not build_base and (base := values["base"]) in const.DEVEL_BASE_STRINGS:
            raise ValueError(
                f"Base {base} requires a build-base (recommended: 'build-base: ubuntu@devel')"
            )
        return build_base


Charm = BasesCharm | PlatformCharm


class Bundle(CharmcraftProject):
    """Model for defining a bundle."""

    type: Literal["bundle"]
    bundle: dict[str, Any] = {}
    name: models.ProjectName | None = None  # type: ignore[assignment]
    title: models.ProjectTitle | None
    summary: CharmcraftSummaryStr | None
    description: pydantic.StrictStr | None
    charmhub: CharmhubConfig = CharmhubConfig()

    @pydantic.root_validator(pre=True)
    def preprocess_bundle(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "name" not in values:
            values["name"] = values.get("bundle", {}).get("name")

        return values
