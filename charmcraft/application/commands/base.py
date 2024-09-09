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
"""Base command for Charmcraft commands."""
from __future__ import annotations

import craft_application.commands

from charmcraft import services


class CharmcraftCommand(craft_application.commands.AppCommand):
    """Base command for Charmcraft commands."""

    format_option: bool = False
    _services: services.CharmcraftServiceFactory

    def fill_parser(self, parser) -> None:
        """Fill the argument parser for this command."""
        super().fill_parser(parser)
        if self.format_option:
            parser.add_argument(
                "--format",
                choices=["json"],
                help="Produce the result in the specified format (currently only 'json')",
            )
