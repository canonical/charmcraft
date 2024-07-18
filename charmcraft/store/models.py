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
"""Internal models for store data structiues."""

import dataclasses
import datetime
import enum
import functools
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from craft_cli import CraftError
from typing_extensions import NotRequired, Self


@dataclasses.dataclass(frozen=True)
class Account:
    """Charmcraft-specific store account model.

    Deprecated in favour of implementation in craft-store.
    """

    name: str
    username: str
    id: str


@dataclasses.dataclass(frozen=True)
class Package:
    """Charmcraft-specific store package model.

    Deprecated in favour of implementation in craft-store.
    """

    id: str | None
    name: str
    type: Literal["charm", "bundle"]


@dataclasses.dataclass(frozen=True)
class MacaroonInfo:
    """Charmcraft-specific macaroon information model.

    Deprecated in favour of implementation in craft-store.
    """

    account: Account
    channels: list[str] | None
    packages: list[Package] | None
    permissions: list[str]


@dataclasses.dataclass(frozen=True)
class Entity:
    """Charmcraft-specific store entity model.

    Deprecated in favour of implementation in craft-store.
    """

    entity_type: Literal["charm", "bundle"]
    name: str
    private: bool
    status: str
    publisher_display_name: str


@dataclasses.dataclass(frozen=True)
class Error:
    """Charmcraft-specific store error model.

    Deprecated in favour of implementation in craft-store.
    """

    message: str
    code: str


@dataclasses.dataclass(frozen=True)
class Uploaded:
    """Charmcraft-specific store upload result model.

    Deprecated in favour of implementation in craft-store.
    """

    ok: bool
    status: int
    revision: int
    errors: list[Error]


@dataclasses.dataclass(frozen=True)
class Base:
    """Charmcraft-specific store object base model.

    Deprecated in favour of implementation in craft-store.
    """

    architecture: str
    channel: str
    name: str


@dataclasses.dataclass(frozen=True)
class Revision:
    """Charmcraft-specific store name revision model.

    Deprecated in favour of implementation in craft-store.
    """

    revision: int
    version: str | None
    created_at: datetime.datetime
    status: str
    errors: list[Error]
    bases: list[Base]


@dataclasses.dataclass(frozen=True)
class Resource:
    """Charmcraft-specific store name resource model.

    Deprecated in favour of implementation in craft-store.
    """

    name: str
    optional: bool
    revision: int
    resource_type: str


@dataclasses.dataclass(frozen=True)
class Release:
    """Charmcraft-specific store release model.

    Deprecated in favour of implementation in craft-store.
    """

    revision: int
    channel: str
    expires_at: datetime.datetime
    resources: list[Resource]
    base: Base


@dataclasses.dataclass(frozen=True)
class Channel:
    """Charmcraft-specific store channel model.

    Deprecated in favour of implementation in craft-store.
    """

    name: str
    fallback: str
    track: str
    risk: str
    branch: str


@dataclasses.dataclass(frozen=True)
class Library:
    """Charmcraft-specific store library model."""

    lib_id: str
    lib_name: str
    charm_name: str
    api: int
    patch: int
    content: str | None
    content_hash: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Self:
        """Convert a dictionary of this type to the type itself.

        Dictionary should match a single item of the `libraries` attribute in
        the response to fetch_libraries or fetch_library
        http://api.charmhub.io/docs/libraries.html#fetch_libraries
        """
        return cls(
            charm_name=value["charm-name"],
            lib_name=value["library-name"],
            lib_id=value["library-id"],
            api=value["api"],
            patch=value["patch"],
            content_hash=value["hash"],
            content=value.get("content"),
        )


@dataclasses.dataclass(frozen=True)
class RegistryCredentials:
    """Charmcraft-specific store registry credential model.

    Deprecated in favour of implementation in craft-store.
    """

    image_name: str
    username: str
    password: str


@functools.total_ordering
@enum.unique
class Risk(enum.Enum):
    """Standard risk tracks for a channel, orderable but not comparable to an int."""

    STABLE = 0
    CANDIDATE = 1
    BETA = 2
    EDGE = 3

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        return NotImplemented


@dataclass(frozen=True)
class ChannelData:
    """Data class for a craft store channel."""

    track: str | None
    risk: Risk
    branch: str | None

    @classmethod
    def from_str(cls, name: str):
        """Parse a channel name from a string using the standard store semantics.

        https://snapcraft.io/docs/channels
        """
        invalid_channel_error = CraftError(f"Invalid channel name: {name!r}")
        parts = name.split("/")
        track: str | None = None
        branch: str | None = None
        if len(parts) == 1:  # Just the risk, e.g. "stable"
            try:
                risk = Risk[parts[0].upper()]
            except KeyError:
                raise invalid_channel_error from None
        elif len(parts) == 2:
            try:  # risk/branch, e.g. "stable/debug"
                risk = Risk[parts[0].upper()]
                branch = parts[1]
            except KeyError:
                try:  # track/risk, e.g. "latest/stable"
                    risk = Risk[parts[1].upper()]
                    track = parts[0]
                except KeyError:
                    raise invalid_channel_error from None
        elif len(parts) == 3:  # Fully defined, e.g. "latest/stable/debug"
            try:
                risk = Risk[parts[1].upper()]
            except KeyError:
                raise invalid_channel_error from None
            track, _, branch = parts
        else:
            raise invalid_channel_error
        return cls(track, risk, branch)

    @property
    def name(self) -> str:
        """Get the channel name as a string."""
        risk = self.risk.name.lower()
        return "/".join(i for i in (self.track, risk, self.branch) if i is not None)


LibraryMetadataRequest = TypedDict(
    "LibraryMetadataRequest",
    {
        "charm-name": str,
        "library-name": str,
        "api": int,
        "patch": NotRequired[int],
    },
)
