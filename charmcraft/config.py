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

"""Central configuration management."""

import datetime
import pathlib
from typing import Any, Dict, List
from urllib.parse import urlparse

import pydantic

from charmcraft.cmdbase import CommandError
from charmcraft.utils import load_yaml


def check_url(value):
    """Check that the URL has at least scheme and net location."""
    if isinstance(value, str):
        url = urlparse(value)
        if url.scheme and url.netloc:
            return value
    raise ValueError(
        "must be a fully qualified URL (such as 'https://some.server.com')"
    )


def check_relative_paths(value):
    """Check that the received paths are all valid relative ones."""
    if isinstance(value, str):
        # check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        # config is independent of the platform where charmcraft is running)
        if value and value[0] != "/":
            return value
    raise ValueError("must be a valid relative path")


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


def format_pydantic_error_msg(msg):
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
        loc = "- field: " + format_pydantic_error_location(error["loc"])
        combined.append(loc)

        msg = "  reason: " + format_pydantic_error_msg(error["msg"])
        combined.append(msg)

    return "\n".join(combined)


class Part(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Placeholder representation for part.  To be replaced by craft-parts."""

    prime: List[pydantic.StrictStr] = []

    @pydantic.validator("prime", each_item=True)
    def validate_relative_paths(cls, prime):
        """Verify relative paths are used in prime."""
        return check_relative_paths(prime)


class Parts(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Represents parts: top-level key.  To be replaced by craft-parts."""

    __root__: Dict[pydantic.StrictStr, Part] = {}

    def get(self, part_name) -> Part:
        """Get part by name.

        :returns: Part if exists, None if not.
        """
        try:
            return self.__root__[part_name]
        except KeyError:
            return None


class CharmhubConfig(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Represents top-level charmhub object."""

    api_url: pydantic.StrictStr = "https://api.charmhub.io"
    storage_url: pydantic.StrictStr = "https://storage.snapcraftcontent.com"

    @pydantic.validator("api_url", "storage_url")
    def validate_urls(cls, url):
        """Verify valid URLs are used for api and storage."""
        return check_url(url)


class Project(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Configuration for all project-related options, used internally."""

    dirpath: pydantic.DirectoryPath
    content: Dict[str, Any] = {}
    config_provided: bool = False
    started_at: datetime.datetime

    @pydantic.validator("dirpath")
    def validate_path(cls, path):
        """Verify valid URLs are used for api and storage."""
        if not isinstance(path, pathlib.Path):
            raise ValueError("invalid path")
        return path


class Config(
    pydantic.BaseModel, extra=pydantic.Extra.forbid, frozen=True, validate_all=True
):
    """Charmcraft config.

    :ivar type: If none, no charmcraft.yaml is present.
    :ivar charmhub: Charmhub configuration.
    :ivar parts: Build parts.
    :ivar project: Project details.
    """

    type: pydantic.StrictStr
    charmhub: CharmhubConfig = CharmhubConfig()
    parts: Parts = Parts()
    project: Project

    @pydantic.validator("type")
    def validate_charm_type(cls, charm_type):
        """Verify charm type is valid with exception when instantiated without YAML."""
        if charm_type not in ["bundle", "charm", "no-charmcraft-yaml"]:
            raise ValueError("must be either 'charm' or 'bundle'")
        return charm_type

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        (1) Perform any necessary translations.

        (2) Standardize error reporting.

        :returns: valid CharmcraftConfig.

        :raises CommandError: On failure to unmarshal object.
        """
        try:
            return cls.parse_obj(obj)
        except pydantic.error_wrappers.ValidationError as error:
            raise CommandError(format_pydantic_errors(error.errors()))


def load(dirpath):
    """Load the config from charmcraft.yaml in the indicated directory."""
    if dirpath is None:
        dirpath = pathlib.Path.cwd()
    else:
        dirpath = pathlib.Path(dirpath).expanduser().resolve()

    # this timestamp will be used in several places, even sent to Charmhub: needs to be UTC
    now = datetime.datetime.utcnow()

    content = load_yaml(dirpath / "charmcraft.yaml")
    if content is None:
        # configuration is mandatory only for some commands; when not provided, it will
        # be initialized all with defaults (but marked as not provided for later verification)
        return Config(
            project=Project(
                dirpath=dirpath,
                content={},
                config_provided=False,
                started_at=now,
            ),
            type="no-charmcraft-yaml",
        )

    else:
        config_provided = True

        # inject project's config
        content["project"] = {
            "dirpath": str(dirpath),
            "content": content,
            "config_provided": config_provided,
            "started_at": str(now),
        }

        return Config.unmarshal(content)
