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

"""Charmcraft Juju Config pydantic model."""

from typing import Dict, Optional

import pydantic

from charmcraft.models.basic import ModelConfigDefaults


class JujuConfig(ModelConfigDefaults):
    """Juju configs for charms.

    See also: https://juju.is/docs/sdk/config
    """

    options: Optional[Dict[str, Dict]]

    @pydantic.validator("options", pre=True)
    def validate_actions(cls, options):
        """Verify options section."""
        for name, option in options.items():
            if not isinstance(option, dict):
                raise ValueError(f"'{name}' is not a dictionary")

            option_keys = set(option.keys())
            if not option_keys.issubset({"description", "type", "default"}):
                invalid_keys = option_keys - {"description", "type", "default"}
                raise ValueError(f"'{name}' has an invalid key(s): {invalid_keys}")

            if "type" not in option:
                raise ValueError(f"'{name}' is missing a type")

            if option["type"] not in ["string", "int", "float", "boolean"]:
                raise ValueError(
                    f"'{option}' has an invalid type '{option['type']}', "
                    "must be one of: string, int, float, boolean"
                )

        return options
