# Copyright 2020-2021 Canonical Ltd.
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

"""Charmcraft manifest.yaml related functionality."""

import datetime
import logging
import pathlib
from typing import Any, Dict, List, Optional

import yaml
import pydantic

from charmcraft import __version__, config
from craft_cli import emit, CraftError

from charmcraft.config import format_pydantic_errors
from charmcraft.linters import CheckResult, CheckType

logger = logging.getLogger(__name__)

CHARM_MANIFEST = "manifest.yaml"


def create_manifest(
    basedir: pathlib.Path,
    started_at: datetime.datetime,
    bases_config: Optional[config.BasesConfiguration],
    linting_results: List[CheckResult],
):
    """Create manifest.yaml in basedir for given base configuration.

    For packing bundles, `bases` will be skipped when bases_config is None.
    Charms should always include a valid bases_config.

    :param basedir: Directory to create Charm in.
    :param started_at: Build start time.
    :param bases_config: Relevant bases configuration, if any.

    :returns: Path to created manifest.yaml.
    """

    content = {
        "charmcraft-version": __version__,
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
        if result.check_type == CheckType.attribute
    ]
    content["analysis"] = {"attributes": attributes_info}

    filepath = basedir / CHARM_MANIFEST
    filepath.write_text(yaml.dump(content))
    return filepath


class CharmManifest(pydantic.BaseModel, frozen=True, validate_all=True):
    """Object representing manifest.yaml contents."""

    bases: Optional[List[config.Base]]

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmManifest.

        :raises CraftError: On failure to unmarshal object.
        """
        try:
            return cls.parse_obj(obj)
        except pydantic.error_wrappers.ValidationError as error:
            raise CraftError(format_pydantic_errors(error.errors(), file_name=CHARM_MANIFEST))


def parse_manifest_yaml(charm_dir: pathlib.Path) -> Optional[CharmManifest]:
    """Parse project's manifest.yaml.

    :returns: a CharmManifest object.

    :raises: CraftError if manifest does not exist.
    """
    manifest_path = charm_dir / CHARM_MANIFEST
    emit.trace(f"Parsing {str(manifest_path)!r}")

    if not manifest_path.exists():
        return None

    with manifest_path.open("rt", encoding="utf8") as fh:
        manifest = yaml.safe_load(fh)
        return CharmManifest.unmarshal(manifest)
