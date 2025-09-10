# Copyright 2023,2025 Canonical Ltd.
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
import warnings
from collections.abc import Iterable
from typing import (
    Annotated,
    Any,
    Literal,
    cast,
)

import pydantic
import pydantic.v1
from craft_application import errors, models
from craft_application.models import PlatformsDict, VersionStr
from craft_application.util import safe_yaml_load
from craft_cli import CraftError, emit
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Self, override

from charmcraft import const, preprocess
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


def _validate_field_name(name: str) -> str:
    """Check that a Juju field name matches Juju's requirements for said field name.

    See the code at:
    https://github.com/juju/juju/blob/60c6895e8ffb9b9952d7971cbdd6df810a572410/mongo/utils/validfield.go#L13-L26
    """
    if not name:
        raise ValueError("A field name cannot be empty.")
    if name.startswith("$"):
        raise ValueError("A field name cannot start with '$'.")
    if "." in name:
        raise ValueError("A field name cannot contain '.'.")
    return name


FieldName = Annotated[str, _validate_field_name]


def get_charm_file_platform_str(bases: Iterable[charmcraft.Base]) -> str:
    """Get the "platform" section of a charm file name from an iterable of bases."""
    base_strings = []
    for base in bases:
        name = base.name
        version = base.channel
        architectures = "-".join(base.architectures)
        base_strings.append(f"{name}-{version}-{architectures}")
    return "_".join(base_strings)


class CharmLib(models.CraftBaseModel):
    """A Charm library dependency for this charm."""

    lib: str = pydantic.Field(
        title="Library Path (e.g. my-charm.my_library)",
        pattern=r"[a-z][a-z0-9_-]+\.[a-z][a-z0-9_]+",
    )
    version: str = pydantic.Field(
        title="Version filter for the charm. Either an API version or a specific [api].[patch].",
        pattern=r"[0-9]+(\.[0-9]+)?",
        coerce_numbers_to_str=False,
        strict=True,
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
            raise ValueError(
                f"API version not valid. Expected an integer, got {api!r}"
            ) from None
        return str(value)

    @pydantic.field_validator("version", mode="before")
    def _validate_patch_version(cls, value: str | float) -> str:
        """Validate the optional patch version, providing a useful error message."""
        if not isinstance(value, str):
            raise ValueError("Input should be a valid string")  # noqa: TRY004
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


class CharmcraftProject(models.Project, metaclass=abc.ABCMeta):
    """A craft-application compatible version of a Charmcraft project.

    This is a Project definition for charmcraft commands that are run through
    craft-application rather than the legacy charmcraft entrypoint. Eventually
    it will be the only form of the project.

    This inherits from CraftBaseModel rather than from the base craft-application Project
    in order to preserve field order. It's registered as a virtual child class below.
    """

    type: Literal["charm"]
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
        default=None,
        description="(DEPRECATED): Configuration for accessing charmhub.",
        deprecated=(
            "The 'charmhub' field is deprecated and no longer used. It will be removed in a "
            f"future release. Use the ${const.STORE_API_ENV_VAR}, ${const.STORE_STORAGE_ENV_VAR} "
            f"and ${const.STORE_REGISTRY_ENV_VAR} environment variables instead."
        ),
    )

    # Default project properties that Charmcraft currently does not use. Types are set
    # to be Optional[None], preventing them from being used, but allow them to be used
    # by the application.

    # Allow setting this - we don't do anything with it though, so we don't show it in the schema.
    version: SkipJsonSchema[VersionStr | None] = None
    license: SkipJsonSchema[None] = None  # pyright: ignore[reportIncompatibleVariableOverride]
    # These are inside the "links" child model.
    contact: SkipJsonSchema[None] = None  # pyright: ignore[reportIncompatibleVariableOverride]
    issues: SkipJsonSchema[None] = None  # pyright: ignore[reportIncompatibleVariableOverride]
    source_code: SkipJsonSchema[None] = None  # pyright: ignore[reportIncompatibleVariableOverride]

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
            raise errors.CraftValidationError(
                "Invalid 'charmcraft.yaml' file",
                details="Support for 'type: bundle' was removed in Charmcraft 4",
                resolution="To create charm bundles, use Charmcraft 3",
                reportable=False,
                docs_url="https://documentation.ubuntu.com/charmcraft/stable/reference/files/charmcraft-yaml-file",
            )
        raise ValueError(f"field type cannot be {project_type!r}")

    @classmethod
    @override
    def from_yaml_data(cls, data: dict[str, Any], filepath: pathlib.Path) -> Self:
        return cls.unmarshal(data)

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

    @pydantic.field_validator("platforms", mode="before")
    @classmethod
    def _preprocess_platforms(
        cls, values: dict[str, dict[str, list[str]] | None]
    ) -> dict[str, dict[str, list[str]]]:
        """Expand the dictionary into the real platforms."""
        platforms = {
            name: value
            if value
            else {
                "build-on": [name],
                "build-for": [name],
            }
            for name, value in values.items()
        }
        for name, value in platforms.items():
            if value.get("build-for") is None:
                value["build-for"] = [name]
        return platforms

    @pydantic.field_validator("parts", mode="before")
    @classmethod
    def _preprocess_parts(
        cls, parts: dict[str, dict[str, Any]] | None, info: pydantic.ValidationInfo
    ) -> dict[str, dict[str, Any]]:
        """Preprocess parts object for a charm, creating an implicit part if needed."""
        if parts is not None and not isinstance(parts, dict):
            raise TypeError(
                "'parts' in charmcraft.yaml must conform to the charmcraft.yaml spec."
            )
        if not parts:
            if "type" in info.data:
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
        return {name: process_part_config(part) for name, part in parts.items()}

    @pydantic.model_validator(mode="after")
    def _warn_charmhub_deprecated(self) -> Self:
        repeat = False
        with warnings.catch_warnings(record=True) as caught:
            if self.charmhub:
                repeat = True
                for warning in caught:
                    if isinstance(warning.message, Warning):
                        message = warning.message.args[0]
                    else:
                        message = warning.message
                    emit.progress(f"WARNING: {message}", permanent=True)
        if repeat:
            for warning in caught:
                warnings.warn(warning.message, stacklevel=1)
        return self


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
              example, ``ubuntu`` or ``almalinux``), a ``channel`` and an
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
    peers: dict[FieldName, Any] | None = pydantic.Field(
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
    provides: dict[FieldName, Any] | None = pydantic.Field(
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
    requires: dict[FieldName, Any] | None = pydantic.Field(
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
    base_str = f"{base['name']}@{base['channel']}"  # pyright: ignore[reportTypedDictNotRequiredAccess]
    return base_str in const.LEGACY_BASES


def _validate_base(
    base: charmcraft.BaseDict | charmcraft.LongFormBasesDict,
) -> charmcraft.LongFormBasesDict:
    if "name" in base:  # Convert short form to long form
        base = cast(
            charmcraft.LongFormBasesDict, {"build-on": [base], "run-on": [base]}
        )
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
        - Alma Linux 9
    """

    # For bases charms, accept anything so we can use platforms internally, but
    # exclude it from serialization and the JSON schema.
    platforms: SkipJsonSchema[Any] = pydantic.Field(
        default=None,
        exclude=True,
        repr=False,
    )

    # This is defined this way because using conlist makes mypy sad and using
    # a ConstrainedList child class has pydantic issues. This appears to be
    # solved with Pydantic 2.
    bases: list[
        Annotated[BasesConfiguration, pydantic.BeforeValidator(_validate_base)]
    ] = pydantic.Field(min_length=1)

    base: None = None

    parts: dict[str, dict[str, Any]] = pydantic.Field(
        default={"charm": {"plugin": "charm", "source": "."}},
        description=textwrap.dedent(
            """\
            Configures the various mechanisms to obtain, process and prepare data from
            different sources that end up being a part of the final charm.

            Keys are user-defined part names. The value of each key is a map where keys
            are part names.

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


class PlatformCharm(CharmProject):
    """Model for defining a charm using Platforms."""

    # Silencing pyright because it complains about missing default value
    base: BaseStr | None = None
    build_base: BuildBaseStr | None = None
    platforms: PlatformsDict

    parts: dict[str, dict[str, Any]] = pydantic.Field(
        description=textwrap.dedent(
            """\
            Configures the various mechanisms to obtain, process and prepare data from
            different sources that end up being a part of the final charm.

            Keys are user-defined part names. The value of each key is a map where keys
            are part names.

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
        min_length=1,
    )

    @pydantic.model_validator(mode="after")
    def _validate_dev_base_needs_build_base(self) -> Self:
        if not self.build_base and self.base in const.DEVEL_BASE_STRINGS:
            raise ValueError(
                f"Base {self.base} requires a build-base (recommended: 'build-base: ubuntu@devel')"
            )
        return self

    @override
    @pydantic.field_validator("platforms", mode="before")
    @classmethod
    def _populate_platforms(cls, platforms: dict[str, Any]) -> dict[str, Any]:
        """Overrides the validator to prevent platforms from being modified.

        Modifying the platforms field can break multi-base builds."""
        return platforms


Charm = PlatformCharm | BasesCharm
