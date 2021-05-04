# Copyright 2020-2021 Canonical Ltd.
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

"""Central configuration management.

Using pydantic's BaseModel, this module supports the translation of the
charmcraft.yaml to a python object.

Configuration schema:

type: [string] one of "charm" or "bundle"

charmhub:
  api_url: [HttpUrl] optional, defaults to "https://api.charmhub.io"
  storage_url: [HttpUrl] optional, defaults to "https://storage.snapcraftcontent.com"

parts:
  bundle:
    prime: [list of strings]

"""

import datetime
import pathlib
from typing import Any, Dict, List, Optional

import pydantic

from charmcraft.cmdbase import CommandError
from charmcraft.utils import load_yaml


class RelativePath(pydantic.StrictStr):
    """Constrainted string which must be a relative path."""

    @classmethod
    def __get_validators__(cls):
        """Yield the relevant validators."""
        yield from super().__get_validators__()
        yield cls.validate_relative_path

    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Validate relative path.

        Check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        config is independent of the platform where charmcraft is running.
        """
        if not value or value[0] == "/":
            raise ValueError("must be a valid relative path")

        return value


def format_pydantic_error_location(loc):
    """Format location."""
    loc_parts = []
    for loc_part in loc:
        if isinstance(loc_part, str):
            loc_parts.append(loc_part)
        elif isinstance(loc_part, int):
            # Integer indicates an index. Go
            # back and fix up previous part.
            previous_part = loc_parts.pop()
            previous_part += f"[{loc_part}]"
            loc_parts.append(previous_part)
        else:
            raise RuntimeError(f"unhandled loc: {loc_part}")

    loc = ".".join(loc_parts)

    # Filter out internal __root__ detail.
    loc = loc.replace(".__root__", "")
    return loc


def format_pydantic_error_message(msg):
    """Format pydantic's error message field."""
    # Replace shorthand "str" with "string".
    msg = msg.replace("str type expected", "string type expected")
    return msg


def format_pydantic_errors(errors):
    """Format errors.

    Example 1: Single error.

    Bad charmcraft.yaml content:
    - field: <some field>
      reason: <some reason>

    Example 2: Multiple errors.

    Bad charmcraft.yaml content:
    - field: <some field>
      reason: <some reason>
    - field: <some field 2>
      reason: <some reason 2>
    """
    combined = ["Bad charmcraft.yaml content:"]
    for error in errors:
        formatted_loc = format_pydantic_error_location(error["loc"])
        formatted_msg = format_pydantic_error_message(error["msg"])

        combined.append(f"- {formatted_msg} in field {formatted_loc!r}")

    return "\n".join(combined)


class Part(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Definition of part to build."""

    prime: List[RelativePath] = []


class Parts(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Definition of parts to build."""

    bundle: Part = Part()

    def get(self, part_name) -> Part:
        """Get part by name.

        :returns: Part if exists, None if not.

        :raises KeyError: if part does not exist.
        """
        if part_name == "bundle":
            return self.bundle
        raise KeyError(part_name)


class CharmhubConfig(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Definition of Charmhub endpoint configuration."""

    api_url: pydantic.HttpUrl = "https://api.charmhub.io"
    storage_url: pydantic.HttpUrl = "https://storage.snapcraftcontent.com"


class Project(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Internal-only project configuration."""

    dirpath: pydantic.DirectoryPath
    config_provided: bool = False

    # this timestamp will be used in several places, even sent to Charmhub: needs to be UTC
    started_at: datetime.datetime = datetime.datetime.utcnow()


class Config(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    frozen=True,
):
    """Definition of charmcraft.yaml configuration."""

    type: Optional[str]
    charmhub: CharmhubConfig = CharmhubConfig()
    parts: Parts = Parts()
    project: Project

    @pydantic.validator("type")
    def validate_charm_type(cls, charm_type, values):
        """Verify charm type is valid with exception when instantiated without YAML."""
        if charm_type not in ["bundle", "charm"]:
            raise ValueError("must be either 'charm' or 'bundle'")
        return charm_type

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any], project: Project):
        """Unmarshal object with necessary translations and error handling.

        (1) Perform any necessary translations.

        (2) Standardize error reporting.

        :returns: valid CharmcraftConfig.

        :raises CommandError: On failure to unmarshal object.
        """
        try:
            # Ensure optional type is specified if loading the yaml.
            # This can be removed once charmcraft.yaml is mandatory.
            if "type" not in obj:
                obj["type"] = None

            return cls.parse_obj({"project": project, **obj})
        except pydantic.error_wrappers.ValidationError as error:
            raise CommandError(format_pydantic_errors(error.errors()))

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


def load(dirpath):
    """Load the config from charmcraft.yaml in the indicated directory."""
    if dirpath is None:
        dirpath = pathlib.Path.cwd()
    else:
        dirpath = pathlib.Path(dirpath).expanduser().resolve()

    now = datetime.datetime.utcnow()

    content = load_yaml(dirpath / "charmcraft.yaml")
    if content is None:
        # configuration is mandatory only for some commands; when not provided, it will
        # be initialized all with defaults (but marked as not provided for later verification)
        return Config(
            project=Project(
                dirpath=dirpath,
                config_provided=False,
                started_at=now,
            ),
        )

    else:
        return Config.unmarshal(
            content,
            project=Project(
                dirpath=dirpath,
                config_provided=True,
                started_at=now,
            ),
        )
