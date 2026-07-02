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

"""Charmcraft Juju Actions pydantic model."""

import keyword
import re
from typing import Any

import pydantic
from craft_application.models import CraftBaseModel

# Must match the action name regex in Juju's charm library:
# https://github.com/juju/charm/blob/6b348d6033da7feecfc7272c6eb752b2e8df2e1e/actions.go#L20
# Action names must be lowercase, may contain digits and internal hyphens,
# and may not contain underscores.
_ACTION_NAME_REGEX = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def validate_action_names_and_bodies(actions: dict[str, Any]) -> None:
    """Validate Juju action names and bodies.

    Raises ValueError or TypeError if any action is invalid.
    """
    if not isinstance(actions, dict):
        raise TypeError("actions.yaml is not a valid actions configuration")
    for name, body in actions.items():
        if keyword.iskeyword(name):
            raise ValueError(
                f"'{name}' is a reserved keyword and cannot be used as an action name"
            )
        if _ACTION_NAME_REGEX.match(name) is None:
            raise ValueError(f"'{name}' is not a valid action name")
        if not isinstance(body, dict):
            raise TypeError(f"action '{name}' must be a mapping")
        if "description" not in body:
            raise ValueError(f"action '{name}' is missing a description")


class JujuActions(CraftBaseModel):
    """Juju actions for charms.

    See also: https://juju.is/docs/sdk/actions
    """

    actions: dict[str, dict] | None

    @pydantic.field_validator("actions", mode="after")
    def validate_actions(cls, actions):
        """Verify actions names and descriptions."""
        validate_action_names_and_bodies(actions)
        return actions
