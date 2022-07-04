# Copyright 2020-2022 Canonical Ltd.
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

"""Logic related to metadata.yaml."""

import pathlib
from typing import Any, Dict

import pydantic
import yaml
from craft_cli import emit, CraftError

from charmcraft.config import format_pydantic_errors

CHARM_METADATA = "metadata.yaml"


class CharmMetadata(pydantic.BaseModel, frozen=True, validate_all=True):
    """Object representing metadata.yaml contents."""

    name: pydantic.StrictStr
    summary: pydantic.StrictStr = ""
    description: pydantic.StrictStr = ""

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmMetadata.

        :raises CraftError: On failure to unmarshal object.
        """
        try:
            return cls.parse_obj(obj)
        except pydantic.error_wrappers.ValidationError as error:
            raise CraftError(format_pydantic_errors(error.errors(), file_name=CHARM_METADATA))


def read_metadata_yaml(charm_dir: pathlib.Path) -> Any:
    """Parse project's metadata.yaml.

    :returns: the YAML decoded metadata.yaml content
    """
    metadata_path = charm_dir / CHARM_METADATA
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
