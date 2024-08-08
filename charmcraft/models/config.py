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
from typing import Annotated, Literal

import pydantic
from craft_application.models import CraftBaseModel


class _BaseJujuOption(CraftBaseModel):
    """A Juju option field. Do not use (use the child classes below)."""

    description: str | None = None
    default: str | int | float | bool | None = None


class JujuStringOption(_BaseJujuOption):
    """A Juju option field containing a string."""

    type: Literal["string"]
    default: str | None = None


class JujuIntOption(_BaseJujuOption):
    """A Juju option field containing an integer."""

    type: Literal["int"]
    default: pydantic.StrictInt | None = None


class JujuFloatOption(_BaseJujuOption):
    """A Juju option field containing a floating-point number."""

    type: Literal["float"]
    default: float | None = None


class JujuBooleanOption(_BaseJujuOption):
    """A Juju option field containing a boolean value."""

    type: Literal["boolean"]
    default: bool | None = None


class JujuSecretOption(_BaseJujuOption):
    """A Juju option field containing a secret ID."""

    type: Literal["secret"]
    # A secret doesn't really make sense, since it's unlikely
    # that anyone would know what the secret ID (specific to
    # the deployment in a model) is at the time that they are
    # writing the config, but included for completeness.
    default: (
        Annotated[str, pydantic.StringConstraints(pattern=r"^secret:[a-z0-9]{20}$")] | None
    ) = None


JujuOption = Annotated[
    JujuStringOption | JujuIntOption | JujuFloatOption | JujuBooleanOption | JujuSecretOption,
    pydantic.Field(discriminator="type"),
]


class JujuConfig(CraftBaseModel):
    """Juju configs for charms.

    See also: https://juju.is/docs/sdk/config
    and: https://juju.is/docs/sdk/config-yaml
    """

    options: dict[str, JujuOption] | None = None
