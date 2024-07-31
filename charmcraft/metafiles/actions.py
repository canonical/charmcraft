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

import logging
import pathlib
import typing
from typing import Literal

import pydantic
from craft_application import util
from craft_application.util.error_formatting import format_pydantic_errors
from craft_cli import CraftError, emit

from charmcraft import const
from charmcraft.models.actions import JujuActions

logger = logging.getLogger(__name__)


@typing.overload
def parse_actions_yaml(
    charm_dir: pathlib.Path, allow_broken: Literal[False] = False
) -> JujuActions: ...


@typing.overload
def parse_actions_yaml(
    charm_dir: pathlib.Path, allow_broken: Literal[True]
) -> JujuActions | None: ...


def parse_actions_yaml(charm_dir, allow_broken=False):
    """Parse project's actions.yaml.

    :param charm_dir: Directory to read actions.yaml from.

    :returns: a JujuActions object or None if actions.yaml does not exist.

    :raises: CraftError if actions.yaml is not valid.
    """
    try:
        with (charm_dir / const.JUJU_ACTIONS_FILENAME).open() as file:
            actions = util.safe_yaml_load(file)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CraftError(f"Cannot read the {const.JUJU_ACTIONS_FILENAME} file: {exc!r}") from exc

    emit.debug(f"Validating {const.JUJU_ACTIONS_FILENAME}")
    try:
        return JujuActions.parse_obj({"actions": actions})
    except pydantic.ValidationError as error:
        if allow_broken:
            emit.progress(
                format_pydantic_errors(error.errors(), file_name=const.JUJU_ACTIONS_FILENAME),
                permanent=True,
            )
            emit.debug(f"Ignoring {const.JUJU_ACTIONS_FILENAME}")
            return None
        raise
