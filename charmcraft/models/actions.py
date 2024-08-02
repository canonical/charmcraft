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

import pydantic
from craft_application.models import CraftBaseModel


class JujuActions(CraftBaseModel):
    """Juju actions for charms.

    See also: https://juju.is/docs/sdk/actions
    """

    _action_name_regex = re.compile(r"^[a-zA-Z_][a-zA-Z0-9-_]*$")
    actions: dict[str, dict] | None

    @pydantic.field_validator("actions", mode="after")
    def validate_actions(cls, actions):
        """Verify actions names and descriptions."""
        if not isinstance(actions, dict):
            raise TypeError("actions.yaml is not a valid actions configuration")
        for action in actions:
            if keyword.iskeyword(action):
                raise ValueError(
                    f"'{action}' is a reserved keyword and cannot be used as an action name"
                )
            if cls._action_name_regex.match(action) is None:
                raise ValueError(f"'{action}' is not a valid action name")

        return actions

    @pydantic.field_validator("actions", mode="after")
    def _validate_actions(cls, action):
        """Verify actions names and descriptions."""
        if not isinstance(action, dict):
            raise TypeError(f"'{action}' is not a dictionary")

        if "description" not in action:
            raise ValueError(f"'{action}' is missing a description")

        return action
