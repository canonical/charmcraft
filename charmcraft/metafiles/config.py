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

import contextlib
import logging
import pathlib
import shutil
from typing import TYPE_CHECKING

import pydantic
import yaml
from craft_cli import CraftError, emit

from charmcraft import const
from charmcraft.format import format_pydantic_errors
from charmcraft.metafiles import read_yaml
from charmcraft.models.config import JujuConfig

if TYPE_CHECKING:
    from charmcraft.models.charmcraft import CharmcraftConfig

logger = logging.getLogger(__name__)


def parse_config_yaml(charm_dir: pathlib.Path, allow_broken=False) -> JujuConfig | None:
    """Parse project's config.yaml.

    :param charm_dir: Directory to read config.yaml from.

    :returns: a JujuConfig object.

    :raises: CraftError if config.yaml is not valid.
    """
    try:
        config = read_yaml(charm_dir / const.JUJU_CONFIG_FILENAME)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CraftError(f"Cannot read the {const.JUJU_CONFIG_FILENAME} file: {exc!r}") from exc

    emit.debug(f"Validating {const.JUJU_CONFIG_FILENAME}")
    try:
        return JujuConfig.parse_obj(config)
    except pydantic.ValidationError as error:
        if allow_broken:
            emit.progress(
                format_pydantic_errors(error.errors(), file_name=const.JUJU_CONFIG_FILENAME),
                permanent=True,
            )
            emit.debug(f"Ignoring {const.JUJU_CONFIG_FILENAME}")
            return None
        raise


def create_config_yaml(
    basedir: pathlib.Path,
    charmcraft_config: "CharmcraftConfig",
) -> pathlib.Path | None:
    """Create actions.yaml in basedir for given project configuration.

    :param basedir: Directory to create Charm in.
    :param charmcraft_config: Charmcraft configuration object.

    :returns: Path to created config.yaml.
    """
    original_file_path = charmcraft_config.project.dirpath / const.JUJU_CONFIG_FILENAME
    target_file_path = basedir / const.JUJU_CONFIG_FILENAME

    # Copy config.yaml if it exists, otherwise create it from CharmcraftConfig.
    if original_file_path.exists():
        # In the build / test process, the original file may be the same as the target file.
        with contextlib.suppress(shutil.SameFileError):
            shutil.copyfile(original_file_path, target_file_path)
    else:
        if charmcraft_config.config:
            target_file_path.write_text(
                yaml.dump(
                    charmcraft_config.config.dict(
                        include={"options"}, exclude_none=True, by_alias=True
                    )
                )
            )
        else:
            return None

    return target_file_path
