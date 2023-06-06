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
from typing import Any, Dict

import yaml
from craft_cli import emit, CraftError

from charmcraft.const import METADATA_FILENAME, CHARM_METADATA_KEYS

logger = logging.getLogger(__name__)


def read_metadata_yaml(charm_dir: pathlib.Path) -> Dict[str, Any]:
    """Parse project's metadata.yaml.

    :returns: the YAML decoded metadata.yaml content
    """
    metadata_path = charm_dir / METADATA_FILENAME
    emit.debug(f"Reading {str(metadata_path)!r}")
    with metadata_path.open("rt", encoding="utf8") as fh:
        return yaml.safe_load(fh)


def parse_metadata_yaml(charm_dir: pathlib.Path) -> Dict[str, Any]:
    """Parse project's metadata.yaml.

    :returns: a metadata dict.

    :raises: CraftError if metadata does not exist.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc
    if not isinstance(metadata, dict):
        raise CraftError(f"The {charm_dir / METADATA_FILENAME} file is not valid YAML.")

    emit.debug("Validating metadata keys")
    for metadata_key in metadata:
        if metadata_key not in CHARM_METADATA_KEYS:
            raise CraftError(f"Unknown metadata key {metadata_key!r}")

    return metadata


def create_metadata(
    charm_dir: pathlib.Path,
    config: Dict[str, Any],
) -> pathlib.Path:
    """Create metadata.yaml in charm_dir for given project configuration.

    Use CHARM_METADATA_KEYS to filter config.

    :param charm_dir: Directory to create Charm in.
    :param config: Charm config dictionary.

    :returns: Path to created metadata.yaml.
    """
    metadata = {k: v for k, v in dict(config).items() if k in CHARM_METADATA_KEYS}

    filepath = charm_dir / "metadata.yaml"
    filepath.write_text(yaml.dump(metadata))
    return filepath
