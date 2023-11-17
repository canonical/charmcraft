# Copyright 2020-2023 Canonical Ltd.
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
"""Version command."""
import argparse
import json

from craft_cli import emit

from charmcraft.application.commands import base


class Version(base.CharmcraftCommand):
    """Show the snapcraft version."""

    name = "version"
    help_msg = "Show the application version and exit"
    overview = "Show the application version and exit"
    common = True
    format_option = True

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the command."""
        format_value = parsed_args.format or ""
        if format_value.lower() == "json":
            emit.message(
                json.dumps(
                    {
                        "application": self._app.name,
                        "version": self._app.version,
                    },
                    indent=4,
                )
            )
            return

        emit.message(f"{self._app.name} {self._app.version}")
