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

import shutil
import pathlib
import logging
from typing import Any, Dict, TYPE_CHECKING

import yaml
from craft_cli import emit, CraftError

from charmcraft.const import METADATA_FILENAME, CHARM_METADATA_KEYS, CHARM_METADATA_KEYS_ALIAS
from charmcraft.models.metadata import CharmMetadataLegacy, BundleMetadataLegacy

if TYPE_CHECKING:
    from charmcraft.models.charmcraft import CharmcraftConfig

logger = logging.getLogger(__name__)


def read_metadata_yaml(charm_dir: pathlib.Path) -> Dict[str, Any]:
    """Parse project's metadata.yaml.

    :returns: the YAML decoded metadata.yaml content
    """
    metadata_path = charm_dir / METADATA_FILENAME
    emit.debug(f"Reading {str(metadata_path)!r}")
    with metadata_path.open("rt", encoding="utf8") as fh:
        return yaml.safe_load(fh)


def parse_charm_metadata_yaml(charm_dir: pathlib.Path) -> CharmMetadataLegacy:
    """Parse project's legacy metadata.yaml that used for charms.

    :returns: a CharmMetadataLegacy object.

    :raises: CraftError if metadata.yaml does not exist or is not valid.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc
    if not isinstance(metadata, dict):
        raise CraftError(f"The {charm_dir / METADATA_FILENAME} file is not valid YAML.")

    emit.debug("Validating metadata keys")
    return CharmMetadataLegacy.unmarshal(metadata)


def parse_bundle_metadata_yaml(charm_dir: pathlib.Path) -> BundleMetadataLegacy:
    """Parse project's legacy metadata.yaml that used for bundles.

    :returns: a BundleMetadataLegacy object.

    :raises: CraftError if metadata.yaml does not exist or is not valid.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc
    if not isinstance(metadata, dict):
        raise CraftError(f"The {charm_dir / METADATA_FILENAME} file is not valid YAML.")

    emit.debug("Validating metadata keys")
    return BundleMetadataLegacy.unmarshal(metadata)


def create_metadata_yaml(
    charm_dir: pathlib.Path,
    charmcraft_config: "CharmcraftConfig",
) -> pathlib.Path:
    """Create metadata.yaml in charm_dir for given project configuration.

    Use CHARM_METADATA_KEYS and CHARM_METADATA_KEYS_ALIAS to filter the keys.

    :param charm_dir: Directory to create Charm in.
    :param charmcraft_config: Charmcraft configuration object.

    :returns: Path to created metadata.yaml.
    """
    file_path = charm_dir / METADATA_FILENAME
    # metadata.yaml should be copied if it exists in the project
    if charmcraft_config.metadata_legacy:
        try:
            shutil.copyfile(charmcraft_config.project.dirpath / METADATA_FILENAME, file_path)
        except shutil.SameFileError:
            pass
    else:
        # metadata.yaml not exists, create it from config
        metadata = charmcraft_config.dict(
            include=CHARM_METADATA_KEYS.union(CHARM_METADATA_KEYS_ALIAS),
            exclude_none=True,
            by_alias=True,
        )

        # convert to legacy metadata format
        if (title := metadata.pop("title", None)) is not None:
            metadata["display-name"] = title

        if (links := metadata.pop("links", None)) is not None:
            if (documentation := links.pop("documentation", None)) is not None:
                metadata["docs"] = documentation
            if (issues := links.pop("issues", None)) is not None:
                metadata["issues"] = issues
            if (contact := links.pop("contact", None)) is not None:
                metadata["maintainers"] = contact
            if (source := links.pop("source", None)) is not None:
                metadata["source"] = source
            if (website := links.pop("website", None)) is not None:
                metadata["website"] = website

        file_path.write_text(yaml.dump(metadata))

    return file_path
