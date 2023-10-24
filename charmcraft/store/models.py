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
from typing import List, Literal, Optional


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
