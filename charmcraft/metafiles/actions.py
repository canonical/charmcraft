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

"""Charmcraft project handle actions.yaml file."""

import contextlib
import logging
import pathlib
import shutil
from typing import TYPE_CHECKING, Optional

import pydantic
import yaml
from craft_cli import CraftError, emit

from charmcraft.const import JUJU_ACTIONS_FILENAME
from charmcraft.format import format_pydantic_errors
from charmcraft.metafiles import read_yaml
from charmcraft.models.actions import JujuActions

if TYPE_CHECKING:
    from charmcraft.models.charmcraft import CharmcraftConfig

logger = logging.getLogger(__name__)


def parse_actions_yaml(charm_dir: pathlib.Path, allow_broken=False) -> Optional[JujuActions]:
    """Parse project's actions.yaml.

    :param charm_dir: Directory to read actions.yaml from.

    :returns: a JujuActions object or None if actions.yaml does not exist.

    :raises: CraftError if actions.yaml is not valid.
    """
    try:
        actions = read_yaml(charm_dir / JUJU_ACTIONS_FILENAME)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CraftError(f"Cannot read the {JUJU_ACTIONS_FILENAME} file: {exc!r}") from exc

    emit.debug(f"Validating {JUJU_ACTIONS_FILENAME}")
    try:
        return JujuActions.parse_obj({"actions": actions})
    except pydantic.ValidationError as error:
        if allow_broken:
            emit.progress(
                format_pydantic_errors(error.errors(), file_name=JUJU_ACTIONS_FILENAME),
                permanent=True,
            )
            emit.debug(f"Ignoring {JUJU_ACTIONS_FILENAME}")
            return None
        raise


def create_actions_yaml(
    basedir: pathlib.Path,
    charmcraft_config: "CharmcraftConfig",
) -> Optional[pathlib.Path]:
    """Create actions.yaml in basedir for given project configuration.

    :param basedir: Directory to create Charm in.
    :param charmcraft_config: Charmcraft configuration object.

    :returns: Path to created actions.yaml.
    """
    original_file_path = charmcraft_config.project.dirpath / JUJU_ACTIONS_FILENAME
    target_file_path = basedir / JUJU_ACTIONS_FILENAME

    # Copy actions.yaml if it exists, otherwise create it from CharmcraftConfig.
    if original_file_path.exists():
        # In the build / test process, the original file may be the same as the target file.
        with contextlib.suppress(shutil.SameFileError):
            shutil.copyfile(original_file_path, target_file_path)
    else:
        if charmcraft_config.actions:
            target_file_path.write_text(
                yaml.dump(
                    charmcraft_config.actions.dict(
                        include={"actions"}, exclude_none=True, by_alias=True
                    )["actions"]
                )
            )
        else:
            return None

    return target_file_path
