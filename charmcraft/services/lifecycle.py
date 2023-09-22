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

"""Service class for packing."""
from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from craft_application.services import LifecycleService
from craft_parts.plugins import plugins

from charmcraft.parts import CharmPlugin, BundlePlugin
from charmcraft.reactive_plugin import ReactivePlugin

if TYPE_CHECKING:  # pragma: no cover
    import pathlib

    from craft_application import models


class CharmLifecycleService(LifecycleService):
    """Business logic for creating packages."""
#
#     def setup(self) -> None:
#
#         super().setup()


