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
import textwrap
from collections.abc import Iterable, Iterator
from typing import (
    Annotated,
    Any,
    Literal,
    cast,
)

import pydantic
import pydantic.v1
from craft_application import errors, models, util
from craft_application.util import safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from pydantic import dataclasses
from typing_extensions import Self

from charmcraft import const, preprocess, utils
from charmcraft.const import (
    BaseStr,
    BuildBaseStr,
)
from charmcraft.models import charmcraft
from charmcraft.models.charmcraft import (
    AnalysisConfig,
    BasesConfiguration,
    Charmhub,
    Links,
)
from charmcraft.parts import process_part_config

CharmcraftSummaryStr = Annotated[
    str,
    models.SummaryStr,
    pydantic.StringConstraints(max_length=200),
    # Maximum length was set to 200 characters because the 78 character maximum
    # inherited from craft-application is too restrictive, as several hundred charms
    # already exceed this maximum.
    # Eventually this limit will be reduced, ideally to 78 characters, though that may
    # never happen entirely. Reductions will only occur on major releases.
    # https://github.com/canonical/charmcraft/issues/1598
]


def get_charm_file_platform_str(bases: Iterable[charmcraft.Base]) -> str:
    """Get the "platform" section of a charm file name from an iterable of bases."""
    base_strings = []
    for base in bases:
        name = base.name
        version = base.channel
        architectures = "-".join(base.architectures)
        base_strings.append(f"{name}-{version}-{architectures}")
    return "_".join(base_strings)


CharmPlatform = Annotated[str, pydantic.StringConstraints(min_length=4, strict=True)]


class CharmLib(models.CraftBaseModel):
    """A Charm library dependency for this charm."""

    lib: str = pydantic.Field(
        title="Library Path (e.g. my-charm.my_library)",
        pattern=r"[a-z][a-z0-9_-]+\.[a-z][a-z0-9_]+",
    )
    version: str = pydantic.Field(
        title="Version filter for the charm. Either an API version or a specific [api].[patch].",
        pattern=r"[0-9]+(\.[0-9]+)?",
    )

    @pydantic.field_validator("lib", mode="before")
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
        return f"{charm_name}.{lib_name}"

    @pydantic.field_validator("version", mode="before")
    def _validate_api_version(cls, value: str) -> str:
        """Validate the API version field, providing a useful error message on failure."""
        api, *_ = str(value).partition(".")
        try:
            int(api)
        except ValueError:
            raise ValueError(f"API version not valid. Expected an integer, got {api!r}") from None
        return str(value)

    @pydantic.field_validator("version", mode="before")
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

        platform = get_charm_file_platform_str(run_on)

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
    platforms: dict[str, models.Platform | None] | None = None  # type: ignore[assignment]

    def get_build_plan(self) -> list[models.BuildInfo]:
        """Get build bases for this charm.

        This method provides a flattened version of every way to build the charm, unfiltered.

        If a charm uses the older "bases" model, it defers to
        `CharmBuildInfo.gen_from_bases_configurations'. Otherwise, it generates the BuildInfo
        as expected with platforms.
        """
        if self.type == "bundle":
            # A bundle can build anywhere, so just present the current system.
            current_arch = util.get_host_architecture()
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
                        platform_name,
                        build_on=platform_name,
                        build_for=platform_name,
                        base=base,
                    )
                )
            else:
                # TODO: this should go to craft-platforms, so silence mypy for now.
                for build_on in platform.build_on:  # type: ignore[union-attr]
                    build_infos.extend(
                        [
                            models.BuildInfo(
                                platform_name,
                                build_on=str(build_on),
                                build_for=str(build_for),
                                base=base,
                            )
                            for build_for in platform.build_for  # type: ignore[union-attr]
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
    title: models.ProjectTitle | None = None
    summary: CharmcraftSummaryStr | None = None
    description: str | None = None

    analysis: AnalysisConfig | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            How analysis done on the charm will behave.

            Currently the only options are to ignore attributes or linters."""
        ),
    )
    charmhub: Charmhub | None = pydantic.Field(
        default=None, description="(DEPRECATED): Configuration for accessing charmhub."
    )
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
    _started_at: datetime.datetime = pydantic.PrivateAttr(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )
    _valid: bool = pydantic.PrivateAttr(default=False)

    @property
    def started_at(self) -> datetime.datetime:
        """Get the time that Charmcraft started running."""
        return self._started_at

    @classmethod
    def unmarshal(cls, data: dict[str, Any]):
        """Create a Charmcraft project from a dictionary of data."""
        if cls is not CharmcraftProject:
            return cls.model_validate(data)
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

    @pydantic.model_validator(mode="before")
    @classmethod
    def _preprocess(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "type" not in values:
            raise ValueError("Project type must be declared in charmcraft.yaml.")

        return values

    @pydantic.field_validator("parts", mode="before")
    @classmethod
    def _preprocess_parts(
        cls, parts: dict[str, dict[str, Any]] | None, info: pydantic.ValidationInfo
    ) -> dict[str, dict[str, Any]]:
        """Preprocess parts object for a charm or bundle, creating an implicit part if needed."""
        if parts is not None and not isinstance(parts, dict):
            raise TypeError("'parts' in charmcraft.yaml must conform to the charmcraft.yaml spec.")
        if not parts:
            if info.config and info.config.get("title") == "Bundle":
                parts = {"bundle": {"plugin": "bundle"}}
            elif "type" in info.data:
                parts = {info.data["type"]: {"plugin": info.data["type"]}}
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
        return {name: process_part_config(part) for name, part in parts.items()}


class CharmProject(CharmcraftProject):
    """A base class for all charm types."""

    type: Literal["charm"]
    """The type of project. Must be the string ``charm``."""
    name: models.ProjectName = pydantic.Field(
        description=textwrap.dedent(
            """\
            The name of the project on Charmhub.

            This value will be used both in the URL of the charm on Charmhub and when
            deploying the charm with juju.

            Charms should follow the
            `charm naming guidelines <https://juju.is/docs/sdk/naming>`_."""
        ),
        examples=[
            "mysql",
            "mysql-k8s",
        ],
    )
    summary: CharmcraftSummaryStr = pydantic.Field(  # pyright: ignore[reportGeneralTypeIssues]
        description="A brief (one-line) summary of your charm.",
    )
    description: str = pydantic.Field(  # pyright: ignore[reportGeneralTypeIssues]
        description="A multi-line summary of your charm."
    )

    parts: dict[str, dict[str, Any]] = pydantic.Field(
        default={"charm": {"plugin": "charm", "source": "."}},
        description=textwrap.dedent(
            """\
            Configures the various mechanisms to obtain, process and prepare data from
            different sources that end up being a part of the final charm.

            Keys are user-defined part names. The value of each key is a map where keys
            are part names. Charmcraft provides 3 plugins: charm, bundle, reactive.

            Example::

                parts:
                  libs:
                    plugin: dump
                    source: /usr/local/lib/
                    organize:
                      "libxxx.so*": lib/
                    prime:
                      - lib/""",
        ),
    )

    actions: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Defines one or more actions.

            This key is equivalent to the
            `actions.yaml file <https://juju.is/docs/sdk/actions-yaml>`_."""
        ),
    )
    assumes: list[str | dict[str, list | dict]] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Explicitly state features a Juju model must be able to provide for a
            successful deployment of this charm. When a charm includes such
            requirements, Juju performs a pre-deployment check and displays
            user-friendly error messages if a feature requirement cannot be met by the
            model that the user is trying to deploy the charm to. If the assumes
            section of the charm metadata is omitted, Juju will make a best-effort
            attempt to deploy the charm, and users must rely on the output of
            ``juju status`` to figure out whether the deployment was successful.

            The key consists of a list of features that can be given either directly
            or, depending on the complexity of the condition you want to enforce,
            nested under one or both of the boolean expressions any-of or all-of,
            as shown below. In order for a charm to be deployed, all entries in the
            assumes block must be satisfied.

            Structure::

                assumes:
                  - <feature-1>
                  - any-of:
                    - <feature-2>
                    - <feature-3>
                  - all-of:
                    - <feature-4>
                    - <feature-5>

            Juju version requirements can be specified with a string such as
            ``juju >= 3.5`` or ``juju < 4.0``. A full list of supported features
            can be found in the
            `Juju documentation <https://juju.is/docs/juju/supported-features>`_.
            """
        ),
    )
    charm_user: Literal["root", "sudoer", "non-root"] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Specifies that the charm code does not need to be run as root. Possible
            values are:

            - ``root``: the charm will run as root
            - ``sudoer``: the charm will run as a non-root user with access to root
              privileges using ``sudo``.
            - ``non-root``: the charm will run as a non-root user without ``sudo``.

            Only affects Kubernetes charms on Juju 3.6.0 or later. If not specified,
            Juju will use
            `its default behaviour <https://juju.is/docs/sdk/metadata-yaml#heading--charm-user>`_.
            """
        ),
    )
    containers: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Define a map of containers to be created adjacent to the charm (as a
            sidecar, in the same pod).

            This is required for Kubernetes charms.

            This key consists of a dictionary mapping container names to their
            specifications. Each container can be specified in terms of ``resource``,
            ``bases`` and ``mounts``, where one of either the ``resource`` or the
            ``bases`` subkeys must be defined and ``mounts`` is optional.

            - ``resource`` is the name of an OCI image resource used to create the
              container (that you will then define further in the resources block).
            - ``bases`` is a list of bases to be used for resolving a container image,
              in descending order of preference. To use it, specify a base name (for
              example, ``ubuntu`` or ``centos``), a ``channel`` and an
              ``architecture``.
            - ``mounts`` is a list of mounted storage volumes for this container. To
              use it, specify the name of the storage to mount from the charm
              storage and, optionally, the location where to mount the storage.

            Structure::

                containers:
                  <container name>:
                    resource: <resource name>
                    bases:
                      - name: <base name>
                        channel: <track[/risk][/branch]>
                        architectures:
                          - <architecture>
                    mounts:
                      - storage: <storage name>
                        location: <path>"""
        ),
        examples=[
            {
                "super-app": {
                    "resource": "super-app-image",
                    "mounts": [{"storage": "logs", "location": "/logs"}],
                }
            }
        ],
    )
    devices: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Devices the charm needs.

            Structure::

                devices:
                  <device name>:
                    type: gpu | nvidia.com/gpu | amd.com/gpu
                    description: <Optional description>
                    countmin: <Optional minimum number requested>
                    countmax: <Optional maximum number requested>"""
        ),
        examples=[
            {
                "amd-gpu": {
                    "type": "amd.com/gpu",
                    "description": "Some sweet AMD GPU",
                    "countmin": 1,
                    "countmax": 100,
                },
                "nvidia-gpu": {
                    "type": "nvidia.com/gpu",
                    "description": "Some NVIDIA GPUs",
                    "countmin": 20,
                },
            },
            {
                "gpus": {
                    "type": "gpu",
                    "description": "A bunch of GPUs",
                    "countmin": 2,
                    "countmax": 40,
                }
            },
        ],
    )
    extra_bindings: dict[str, Any] | None = pydantic.Field(
        default=None,
        description="A key-only mapping representing extra bindings needed.",
    )
    peers: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            A map of peer relations.

            Structure::

                peers:
                  <endpoint name>:
                    interface: <Required interface name>
                    limit: <Optional: maximum number of supported connections
                    optional: <Informational only - whether the relation is required.>
                    scope: <"global" or "container" - the relation scope.>

            For more information, see
            `the Juju documentation <https://juju.is/docs/juju/relation>`_."""
        ),
        examples=[
            {
                "friend": {
                    "interface": "life",
                    "limit": 150,
                    "optional": True,
                    "scope": "container",
                }
            }
        ],
    )
    provides: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            A map of interfaces this charm provides.

            Structure::

                provides:
                  <endpoint name>:
                    interface: <Required interface name>
                    limit: <Optional: maximum number of supported connections
                    optional: <Informational only - whether the relation is required.>
                    scope: <"global" or "container" - the relation scope.>

            For more information, see
            `the Juju documentation <https://juju.is/docs/juju/relation>`_."""
        ),
        examples=[{"self": {"interface": "identity"}}],
    )
    requires: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            A map of relations this charm requires.

            Structure::

                requires:
                  <endpoint name>:
                    interface: <Required interface name>
                    limit: <Optional: maximum number of supported connections
                    optional: <Informational only - whether the relation is required.>
                    scope: <"global" or "container" - the relation scope.>

            For more information, see
            `the Juju documentation <https://juju.is/docs/juju/relation>`_."""
        ),
        examples=[
            {
                "parent": {
                    "interface": "birth",
                    "limit": 2,
                    "optional": False,
                    "scope": "global",
                }
            }
        ],
    )
    resources: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            A mapping of resources that accompany the charm.

            See first: `Juju | Charm resource <https://juju.is/docs/juju/charm-resource>`_

            Each resource is made available when the charm is deployed. NOTE:
            Kubernetes charms must declare an ``oci-image`` type resource for each
            container declared in ``containers``.

            Structure::

                # (Optional) Additional resources that accompany the charm
                resources:
                  <resource name>:
                    # (Required) The type of the resource
                    type: file | oci-image

                    # (Optional) Description of the resource and its purpose
                    description: <description>

                    # (Required: when type:file) The filename of the resource as it
                    # should appear in the filesystem.
                    filename: <filename>"""
        ),
        examples=[
            {"water": {"type": "file", "filename": "/dev/h2o"}},
            {"super-app-image": {"type": "oci-image", "description": "My app!"}},
        ],
    )
    storage: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            Storage devices requested by the charm.

            Structure::

                storage:
                  # Each key represents the name of the storage
                  <storage name>:

                    # (Required) Type of the requested storage
                    type: filesystem | block

                    # (Optional) Description of the storage requested
                    description: <description>

                    # (Optional) The mount location for filesystem stores. For
                    # multi-stores the location acts as the parent directory for each
                    # mounted store.
                    location: <location>

                    # Indicates if all units of the application share the storage.
                    # Defaults to false
                    shared: true | false

                    # Indicates if the storage should be made read-only (where
                    # possible). Defaults to false
                    read-only: true | false

                    # (Optional) The number of storage instances to be requested
                    multiple:
                      range: <n> | <n>-<m> | <n>- | <n>+

                    # (Optional) Minimum size of requested storage in forms G, GiB, GB.
                    # Size multipliers are M, G, T, P, E, Z or Y. With no multiplier
                    # supplied, M is implied.
                    minimum-size: <n> | <n><multiplier>

                    # (Optional) List of properties, only supported value is "transient"
                    properties:
                      - transient
            """
        ),
        examples=[
            {
                "jbod": {
                    "type": "block",
                    "description": "A block storage to use as swap space",
                    "shared": False,
                    "properties": ["transient"],
                },
            },
        ],
    )
    subordinate: bool | None = pydantic.Field(
        default=None,
        description="Optional boolean to declare the charm subordinate.",
        examples=[True],
    )
    terms: list[str] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            A list of terms to which the user agree by using the charm.
            These terms are not enforced by the charm, Juju or Canonical."""
        ),
        examples=[
            "Post cat pictures on Mastodon",
            "Tag your cat pictures with #caturday",
        ],
    )
    links: Links | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            (Recommended) Links to various additional information used by Charmhub."""
        ),
        examples=[
            {
                "contact": "Please send your answer to Old Pink, care of the Funny Farm, Chalfont",
                "documentation": "https://discourse.charmhub.io/t/traefik-k8s-docs-index/10778",
                "issues": "https://github.com/canonical/traefik-k8s-operator/issues",
                "source": "https://github.com/canonical/traefik-k8s-operator",
                "website": "https://charmed-kubeflow.io/",
            }
        ],
    )
    config: dict[str, Any] | None = pydantic.Field(
        default=None,
        description=textwrap.dedent(
            """\
            One or more configuration options for your charm.

            Structure::

                config:
                  options:
                    # Each option name is the name by which the charm will query the option.
                    <option name>:
                      # (Required) The type of the option
                      type: string | int | float | boolean | secret
                      # (Optional) The default value of the option
                      default: <a reasonable default value of the same type as the option>
                      # (Optional): A string describing the option. Also appears on charmhub.io
                      description: <description string>"""
        ),
        examples=[
            {
                "options": {
                    "name": {
                        "default": "Wiki",
                        "description": "The name or title of the Wiki",
                        "type": "string",
                    },
                    "skin": {
                        "default": "vector",
                        "description": "Skin to use for the wiki",
                        "type": "string",
                    },
                },
            },
        ],
    )


def _check_base_is_legacy(base: charmcraft.BaseDict) -> bool:
    """Check that the given base is a legacy base, usable with 'bases'."""
    # This pyright ignore can go away once we're on Python minimum version 3.11.
    # At that point we can mark items as required or not required.
    # https://docs.python.org/3/library/typing.html#typing.Required
    if (
        base["name"] == "ubuntu"  # pyright: ignore[reportTypedDictNotRequiredAccess]
        and base["channel"] < "24.04"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    ):
        return True
    return base in ({"name": "centos", "channel": "7"}, {"name": "almalinux", "channel": "9"})


def _validate_base(
    base: charmcraft.BaseDict | charmcraft.LongFormBasesDict,
) -> charmcraft.LongFormBasesDict:
    if "name" in base:  # Convert short form to long form
        base = cast(charmcraft.LongFormBasesDict, {"build-on": [base], "run-on": [base]})
    else:  # Cast to long form since we know it is one.
        base = cast(charmcraft.LongFormBasesDict, base)

    # Ensure we're only allowing legacy bases.
    for build_base in base["build-on"]:
        if not _check_base_is_legacy(build_base):
            raise ValueError(f"Base requires 'platforms' definition: {build_base}")
    for run_base in base["run-on"]:
        if not _check_base_is_legacy(run_base):
            raise ValueError(f"Base requires 'platforms' definition: {run_base}")
    return base


class BasesCharm(CharmProject):
    """A charm using the deprecated ``bases`` keyword.

    This type of charm only supports the following bases:
        - Ubuntu 18.04
        - Ubuntu 20.04
        - Ubuntu 22.04
        - CentOS 7
        - Alma Linux 9
    """

    platforms: None = None  # type: ignore[assignment]

    # This is defined this way because using conlist makes mypy sad and using
    # a ConstrainedList child class has pydantic issues. This appears to be
    # solved with Pydantic 2.
    bases: list[Annotated[BasesConfiguration, pydantic.BeforeValidator(_validate_base)]] = (
        pydantic.Field(min_length=1)
    )

    base: None = None


class PlatformCharm(CharmProject):
    """Model for defining a charm using Platforms."""

    # Silencing pyright because it complains about missing default value
    base: BaseStr  # pyright: ignore[reportGeneralTypeIssues]
    build_base: BuildBaseStr | None = None
    platforms: dict[str, models.Platform | None]  # type: ignore[assignment]

    @pydantic.model_validator(mode="after")
    def _validate_dev_base_needs_build_base(self) -> Self:
        if not self.build_base and self.base in const.DEVEL_BASE_STRINGS:
            raise ValueError(
                f"Base {self.base} requires a build-base (recommended: 'build-base: ubuntu@devel')"
            )
        return self


Charm = BasesCharm | PlatformCharm


class Bundle(CharmcraftProject):
    """Model for defining a bundle."""

    type: Literal["bundle"]
    bundle: dict[str, Any] = {}
    name: models.ProjectName | None = None  # type: ignore[assignment]
    title: models.ProjectTitle | None = None
    summary: CharmcraftSummaryStr | None = None
    description: pydantic.StrictStr | None = None
    platforms: None = None  # type: ignore[assignment]

    @pydantic.model_validator(mode="before")
    @classmethod
    def preprocess_bundle(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Preprocess any values that charmcraft infers, before attribute validation."""
        if "name" not in values:
            values["name"] = values.get("bundle", {}).get("name")

        return values
