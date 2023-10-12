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

"""Handlers for manifest.yaml file."""

import datetime
import json
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional

import yaml
from craft_cli import CraftError

import charmcraft.linters
import charmcraft.models.charmcraft
from charmcraft.const import IMAGE_INFO_ENV_VAR

logger = logging.getLogger(__name__)


def create_manifest(
    basedir: pathlib.Path,
    started_at: datetime.datetime,
    bases_config: Optional[charmcraft.models.charmcraft.BasesConfiguration],
    linting_results: List[charmcraft.linters.CheckResult],
) -> pathlib.Path:
    """Create manifest.yaml in basedir for given base configuration.

    For packing bundles, `bases` will be skipped when bases_config is None.
    Charms should always include a valid bases_config.

    :param basedir: Directory to create Charm in.
    :param started_at: Build start time.
    :param bases_config: Relevant bases configuration, if any.

    :returns: Path to created manifest.yaml.
    """
    content: Dict[str, Any] = {
        "charmcraft-version": charmcraft.__version__,
        "charmcraft-started-at": started_at.isoformat() + "Z",
    }

    # Annotate bases only if bases_config is not None.
    if bases_config is not None:
        bases = [
            {
                "name": r.name,
                "channel": r.channel,
                "architectures": r.architectures,
            }
            for r in bases_config.run_on
        ]
        content["bases"] = bases

    # include the linters results (only for attributes)
    attributes_info = [
        {"name": result.name, "result": result.result}
        for result in linting_results
        if result.check_type == charmcraft.linters.CheckType.ATTRIBUTE
    ]
    content["analysis"] = {"attributes": attributes_info}

    # include the image info, if present
    image_info_raw = os.environ.get(IMAGE_INFO_ENV_VAR)
    if image_info_raw:
        try:
            image_info = json.loads(image_info_raw)
        except json.decoder.JSONDecodeError as exc:
            msg = f"Failed to parse the content of {IMAGE_INFO_ENV_VAR} environment variable"
            raise CraftError(msg) from exc
        content["image-info"] = image_info

    filepath = basedir / "manifest.yaml"
    filepath.write_text(yaml.dump(content))
    return filepath
