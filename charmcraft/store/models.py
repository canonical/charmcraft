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
from typing import List, Literal, Optional

from craft_cli import CraftError


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

    id: Optional[str]
    name: str
    type: Literal["charm", "bundle"]


@dataclasses.dataclass(frozen=True)
class MacaroonInfo:
    """Charmcraft-specific macaroon information model.

    Deprecated in favour of implementation in craft-store.
    """

    account: Account
    channels: Optional[List[str]]
    packages: Optional[List[Package]]
    permissions: List[str]


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
    errors: List[Error]


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
    version: Optional
    created_at: datetime.datetime
    status: str
    errors: List[Error]
    bases: List[Base]


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
class ResourceRevision:
    """Charmcraft-specific store resource revision model.

    Deprecated in favour of implementation in craft-store.
    """

    revision: int
    created_at: datetime.datetime
    size: int


@dataclasses.dataclass(frozen=True)
class Release:
    """Charmcraft-specific store release model.

    Deprecated in favour of implementation in craft-store.
    """

    revision: int
    channel: str
    expires_at: datetime.datetime
    resources: List[Resource]
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
    """Charmcraft-specific store library model.

    Deprecated in favour of implementation in craft-store.
    """

    lib_id: str
    lib_name: str
    charm_name: str
    api: int
    patch: int
    content: Optional[str]
    content_hash: str


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

    track: Optional[str]
    risk: Risk
    branch: Optional[str]

    @classmethod
    def from_str(cls, name: str):
        """Parse a channel name from a string using the standard store semantics.

        https://snapcraft.io/docs/channels
        """
        invalid_channel_error = CraftError(f"Invalid channel name: {name!r}")
        parts = name.split("/")
        track: Optional[str] = None
        branch: Optional[str] = None
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


@dataclasses.dataclass(frozen=True)
class CharmhubConfig:
    """Definition of Charmhub endpoint configuration."""

    api_url: str = "https://api.charmhub.io"
    storage_url: str = "https://storage.snapcraftcontent.com"
    registry_url: str = "https://registry.jujucharms.com"
