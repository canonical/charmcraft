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

import contextlib
import logging
import pathlib
import shutil
from typing import TYPE_CHECKING, Any

import pydantic
import yaml
from craft_cli import CraftError, emit

from charmcraft import const
from charmcraft.format import format_pydantic_errors
from charmcraft.models.metadata import BundleMetadata, CharmMetadataLegacy

if TYPE_CHECKING:
    from charmcraft.models.charmcraft import CharmcraftConfig

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
    original_file_path = charmcraft_config.project.dirpath / const.METADATA_FILENAME
    target_file_path = charm_dir / const.METADATA_FILENAME

    # Copy metadata.yaml if it exists, otherwise create it from CharmcraftConfig.
    if original_file_path.exists():
        # In the build / test process, the original file may be the same as the target file.
        with contextlib.suppress(shutil.SameFileError):
            shutil.copyfile(original_file_path, target_file_path)
    else:
        # metadata.yaml not exists, create it from config
        metadata = charmcraft_config.dict(
            include=const.CHARM_METADATA_KEYS.union(const.CHARM_METADATA_KEYS_ALIAS),
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

        target_file_path.write_text(yaml.dump(metadata))

    return target_file_path
