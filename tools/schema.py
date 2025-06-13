#!/usr/bin/env python3
#
# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Creation of schema for charmcraft.yaml."""

import json

from charmcraft.models.project import PlatformCharm, BasesCharm
from typing import Annotated, Any
import pydantic

def _charm_type_discriminator(charm_model: Any) -> str:  # noqa: ANN401
    if hasattr(charm_model, "platforms") or "platforms" in charm_model:
        return "platformcharm"
    return "basescharm"

Charm = Annotated[
    Annotated[PlatformCharm, pydantic.Tag("platformcharm")]
    | Annotated[BasesCharm, pydantic.Tag("basescharm")],
    pydantic.Discriminator(_charm_type_discriminator)
]

if __name__ == "__main__":
    print(json.dumps(pydantic.TypeAdapter(Charm).json_schema(), indent="	"))
