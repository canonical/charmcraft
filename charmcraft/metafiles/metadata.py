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

"""Handlers for metadata.yaml file."""

import pathlib
import logging
from typing import Any

import yaml
from craft_cli import emit, CraftError

from charmcraft.const import METADATA_FILENAME
from charmcraft.models.metadata import CharmMetadata

logger = logging.getLogger(__name__)


def read_metadata_yaml(charm_dir: pathlib.Path) -> Any:
    """Parse project's metadata.yaml.

    :returns: the YAML decoded metadata.yaml content
    """
    metadata_path = charm_dir / METADATA_FILENAME
    emit.debug(f"Reading {str(metadata_path)!r}")
    with metadata_path.open("rt", encoding="utf8") as fh:
        return yaml.safe_load(fh)


def parse_metadata_yaml(charm_dir: pathlib.Path) -> CharmMetadata:
    """Parse project's metadata.yaml.

    :returns: a CharmMetadata object.

    :raises: CraftError if metadata does not exist.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc

    emit.debug("Validating metadata format")
    return CharmMetadata.unmarshal(metadata)
