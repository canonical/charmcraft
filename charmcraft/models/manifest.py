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
"""Model for output charm's manifest.yaml file."""
from typing import Any, Literal

from craft_application import models

import charmcraft
from charmcraft.models.charmcraft import Base


class Attribute(models.BaseMetadata):
    """An attribute as a linter result."""

    name: str
    result: str


class Manifest(models.BaseMetadata):
    """A manifest.yaml file for Juju.

    See: https://juju.is/docs/sdk/manifest-yaml
    """

    charmcraft_version: str = charmcraft.__version__
    charmcraft_started_at: str
    bases: list[Base] | None
    analysis: dict[Literal["attributes"], list[Attribute]] = {"attributes": []}
    image_info: Any | None = None
