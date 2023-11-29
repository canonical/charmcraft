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

import tabulate
import yaml
from craft_cli import emit

from charmcraft import extensions
from charmcraft.cmdbase import BaseCommand
from charmcraft.models.extension import ExtensionModel

_overview = """
Extensions allow user use pre-defined configuration in their charmcraft.yaml.
"""


class ListExtensionsCommand(BaseCommand):
    """List available extensions for all supported bases."""

    common = True
    name = "list-extensions"
    help_msg = "List available extensions for all supported bases"
    overview = dedent(
        """
        List available extensions and their corresponding bases.
        """
    )

    def run(self, parsed_args: argparse.Namespace):
        """Print the list of available extensions and their bases."""
        extension_presentation: dict[str, ExtensionModel] = {}

        for extension_name in extensions.registry.get_extension_names():
            extension_class = extensions.registry.get_extension_class(extension_name)
            extension_bases = list(extension_class.get_supported_bases())
            extension_presentation[extension_name] = ExtensionModel(
                name=extension_name, bases=extension_bases
            )

        printable_extensions = sorted(
            [v.marshal() for v in extension_presentation.values()],
            key=lambda d: d["Extension name"],
        )
        emit.message(tabulate.tabulate(printable_extensions, headers="keys"))


class ExtensionsCommand(ListExtensionsCommand):
    """A command alias to list the available extensions."""

    common = False
    name = "extensions"
    hidden = True

    # Workaround for AST test that cannot see run()
    def run(self, parsed_args: argparse.Namespace):
        """Print the list of available extensions and their bases."""
        ListExtensionsCommand.run(self, parsed_args)


class ExpandExtensionsCommand(BaseCommand):
    """Expand the extensions in the charmcraft.yaml file."""

    common = True
    name = "expand-extensions"
    help_msg = "Expand extensions in charmcraft.yaml"
    overview = dedent(
        """
        Extensions listed charmcraft.yaml will be
        expanded and shown as output.
        """
    )

    def run(self, parsed_args: argparse.Namespace):
        """Print the project's specification with the extensions expanded."""
        self._check_config(config_file=True)
        emit.message(
            yaml.dump(
                self.config.dict(
                    by_alias=True, exclude={"project", "metadata_legacy"}, exclude_none=True
                )
            )
        )
