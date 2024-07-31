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

import logging
import pathlib

import pydantic
from craft_application.util.error_formatting import format_pydantic_errors
from craft_cli import CraftError, emit

from charmcraft import const
from charmcraft.metafiles import read_yaml
from charmcraft.models.config import JujuConfig

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

    if allow_broken and (not isinstance(config, dict) or not config.get("options")):
        emit.progress(
            "'config.yaml' is not a valid config file.",
            permanent=True,
        )
        emit.debug(f"Ignoring {const.JUJU_CONFIG_FILENAME}")
        return None

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
