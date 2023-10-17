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
import datetime
import itertools
import json
import os
from typing import Any, List, Optional

from craft_application import models
from craft_cli import CraftError
from typing_extensions import Self

import charmcraft
from charmcraft.const import IMAGE_INFO_ENV_VAR
from charmcraft.models.charmcraft import Base
from charmcraft.models.project import Charm


class Manifest(models.BaseMetadata):
    """A manifest.yaml file for Juju.

    See: https://juju.is/docs/sdk/manifest-yaml
    """

    charmcraft_version: str = charmcraft.__version__
    charmcraft_started_at: datetime.datetime
    bases: Optional[List[Base]]
    # TODO: Linter results under "analysis"
    image_info: Optional[Any]

    @classmethod
    def from_charm(cls, charm: Charm) -> Self:
        """Generate a manifest from a Charmcraft project."""
        params = {
            "charmcraft-started-at": charm.started_at,
            "bases": list(itertools.chain.from_iterable(base.run_on for base in charm.bases)),
        }
        # TODO: analysis
        if IMAGE_INFO_ENV_VAR in os.environ:
            try:
                params["image-info"] = json.loads(os.getenv(IMAGE_INFO_ENV_VAR))
            except json.decoder.JSONDecodeError as exc:
                msg = f"Failed to parse the content of {IMAGE_INFO_ENV_VAR} environment variable"
                raise CraftError(msg) from exc
        return cls.parse_obj(params)
