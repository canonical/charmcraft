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
"""Store module for Charmcraft."""

from charmcraft.store.client import build_user_agent, AnonymousClient, Client
from charmcraft.store import models
from charmcraft.store.models import LibraryMetadataRequest
from charmcraft.store.registry import (
    OCIRegistry,
    HashingTemporaryFile,
    LocalDockerdInterface,
    ImageHandler,
)
from charmcraft.store.store import Store, AUTH_DEFAULT_TTL, AUTH_DEFAULT_PERMISSIONS

__all__ = [
    "build_user_agent",
    "AnonymousClient",
    "Client",
    "OCIRegistry",
    "HashingTemporaryFile",
    "ImageHandler",
    "LocalDockerdInterface",
    "AUTH_DEFAULT_PERMISSIONS",
    "AUTH_DEFAULT_TTL",
    "Store",
    "models",
    "LibraryMetadataRequest",
]
