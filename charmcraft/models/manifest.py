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
import itertools
import json
import os
from collections.abc import Iterable
from typing import Any, Literal

from craft_application import models
from craft_cli import CraftError
from typing_extensions import Self

import charmcraft
from charmcraft.const import IMAGE_INFO_ENV_VAR
from charmcraft.linters import CheckResult, CheckType
from charmcraft.models.charmcraft import Base
from charmcraft.models.project import Charm


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
    image_info: Any | None

    @classmethod
    def from_charm_and_lint(cls, charm: Charm, lint_results: Iterable[CheckResult]) -> Self:
        """Generate a manifest from a Charmcraft project."""
        attributes: list[Attribute] = []
        params = {
            "charmcraft-version": charmcraft.__version__,
            "charmcraft-started-at": charm.started_at.isoformat(),
            "bases": list(itertools.chain.from_iterable(base.run_on for base in charm.bases)),
            "analysis": {"attributes": attributes},
        }

        for result in lint_results:
            if result.check_type != CheckType.ATTRIBUTE:
                continue
            attributes.append(Attribute(name=result.name, result=result.result))

        image_info = os.getenv(IMAGE_INFO_ENV_VAR)
        if image_info is not None:
            try:
                params["image-info"] = json.loads(image_info)
            except json.decoder.JSONDecodeError as exc:
                msg = f"Failed to parse the content of {IMAGE_INFO_ENV_VAR} environment variable"
                raise CraftError(msg) from exc
        return cls.parse_obj(params)
