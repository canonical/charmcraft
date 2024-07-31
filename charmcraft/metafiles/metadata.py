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

import logging
import pathlib
from typing import Any

import pydantic
import yaml
from craft_application.util.error_formatting import format_pydantic_errors
from craft_cli import CraftError, emit

from charmcraft import const
from charmcraft.models.metadata import BundleMetadata, CharmMetadataLegacy

logger = logging.getLogger(__name__)


def read_metadata_yaml(charm_dir: pathlib.Path) -> dict[str, Any]:
    """Parse project's metadata.yaml.

    :returns: the YAML decoded metadata.yaml content
    """
    metadata_path = charm_dir / const.METADATA_FILENAME
    emit.debug(f"Reading {str(metadata_path)!r}")
    with metadata_path.open("rt", encoding="utf8") as fh:
        return yaml.safe_load(fh)


def parse_charm_metadata_yaml(
    charm_dir: pathlib.Path, allow_basic: bool = False
) -> CharmMetadataLegacy:
    """Parse project's legacy metadata.yaml that used for charms.

    :returns: a CharmMetadataLegacy object.

    :raises: CraftError if metadata.yaml does not exist or is not valid.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc
    if not isinstance(metadata, dict):
        raise CraftError(f"The {charm_dir / const.METADATA_FILENAME} file is not valid YAML.")

    emit.debug("Validating metadata keys")
    try:
        return CharmMetadataLegacy.unmarshal(metadata)
    except pydantic.ValidationError as error:
        if allow_basic:
            emit.progress(
                format_pydantic_errors(error.errors(), file_name=const.METADATA_FILENAME),
                permanent=True,
            )
            emit.debug("Falling back to basic metadata.yaml")
            metadata_basic = {
                k: v for k, v in metadata.items() if k in ("name", "summary", "description")
            }
            return CharmMetadataLegacy.unmarshal(metadata_basic)
        raise


def parse_bundle_metadata_yaml(charm_dir: pathlib.Path) -> BundleMetadata:
    """Parse project's legacy metadata.yaml that used for bundles.

    :returns: a BundleMetadataLegacy object.

    :raises: CraftError if metadata.yaml does not exist or is not valid.
    """
    try:
        metadata = read_metadata_yaml(charm_dir)
    except OSError as exc:
        raise CraftError(f"Cannot read the metadata.yaml file: {exc!r}") from exc
    if not isinstance(metadata, dict):
        raise CraftError(f"The {charm_dir / const.METADATA_FILENAME} file is not valid YAML.")

    emit.debug("Validating metadata keys")
    return BundleMetadata.unmarshal(metadata)
