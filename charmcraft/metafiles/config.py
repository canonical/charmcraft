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

"""Charmcraft project handle config.yaml file."""

import pathlib
import logging
import shutil
from typing import Optional, TYPE_CHECKING

import yaml

from craft_cli import emit, CraftError
from charmcraft.const import JUJU_CONFIG_FILENAME
from charmcraft.models.config import JujuConfig
from charmcraft.metafiles import read_yaml

if TYPE_CHECKING:
    from charmcraft.models.charmcraft import CharmcraftConfig

logger = logging.getLogger(__name__)


def parse_config_yaml(charm_dir: pathlib.Path) -> Optional[JujuConfig]:
    """Parse project's config.yaml.

    :param charm_dir: Directory to read config.yaml from.

    :returns: a JujuConfig object.

    :raises: CraftError if config.yaml is not valid.
    """
    try:
        config = read_yaml(charm_dir / JUJU_CONFIG_FILENAME)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CraftError(f"Cannot read the {JUJU_CONFIG_FILENAME} file: {exc!r}") from exc

    emit.debug(f"Validating {JUJU_CONFIG_FILENAME}")
    return JujuConfig.parse_obj({"legacy": True, **config})


def create_config_yaml(
    basedir: pathlib.Path,
    charmcraft_config: "CharmcraftConfig",
) -> Optional[pathlib.Path]:
    """Create actions.yaml in basedir for given project configuration.

    :param basedir: Directory to create Charm in.
    :param charmcraft_config: Charmcraft configuration object.

    :returns: Path to created config.yaml.
    """
    if charmcraft_config.config is None or charmcraft_config.config.options is None:
        return None

    file_path = basedir / JUJU_CONFIG_FILENAME

    if charmcraft_config.config.legacy:
        try:
            shutil.copyfile(charmcraft_config.project.dirpath / JUJU_CONFIG_FILENAME, file_path)
        except shutil.SameFileError:
            pass
    else:
        file_path.write_text(
            yaml.dump(
                charmcraft_config.config.dict(
                    include={"options"}, exclude_none=True, by_alias=True
                )
            )
        )

    return file_path
