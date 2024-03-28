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

"""Infrastructure for the 'extensions' command."""
import argparse
from textwrap import dedent

from craft_cli import emit

from charmcraft import extensions, utils
from charmcraft.application.commands import base


class ListExtensionsCommand(base.CharmcraftCommand):
    """List available extensions for all supported bases."""

    common = True
    name = "list-extensions"
    help_msg = "List available extensions for all supported bases"
    overview = dedent(
        """
        List available extensions and their corresponding bases.
        """
    )
    format_option = True

    def run(self, parsed_args: argparse.Namespace):
        """Print the list of available extensions and their bases."""
        extension_data = extensions.registry.get_extensions()

        if not parsed_args.format:
            extension_data = [
                {
                    "Extension name": ext["name"],
                    "Supported bases": ", ".join(ext["bases"]),
                    "Experimental bases": ", ".join(ext["experimental_bases"]),
                }
                for ext in extension_data
            ]

        emit.message(
            utils.format_content(
                extension_data,
                fmt=parsed_args.format or utils.OutputFormat.TABLE,
            )
        )


class ExtensionsCommand(ListExtensionsCommand):
    """A command alias to list the available extensions."""

    common = False
    name = "extensions"
    hidden = True


class ExpandExtensionsCommand(base.CharmcraftCommand):
    """Expand the extensions in the charmcraft.yaml file."""

    common = True
    name = "expand-extensions"
    help_msg = "Expand extensions in charmcraft.yaml"
    overview = dedent(
        """
        Expand charmcraft.yaml using the extensions specified in the file and
        output the resulting configuration to the terminal.

        This allows you to see how the extensions used modify your existing
        charmcraft.yaml file.
        """
    )
    always_load_project = True

    def fill_parser(self, parser) -> None:
        """Fill in the parser for this command."""
        super().fill_parser(parser)

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Print the project's specification with the extensions expanded."""
        emit.message(utils.dump_yaml(self._services.project.marshal()))
