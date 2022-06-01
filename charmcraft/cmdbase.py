# Copyright 2020-2022 Canonical Ltd.
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

"""Infrastructure for common base commands functionality."""

import json

import craft_cli

JSON_FORMAT = "json"


class BaseCommand(craft_cli.BaseCommand):
    """Subclass this to create a new command.

    The following default attribute is provided beyond craft-cli ones:

    - needs_config: will ensure a config is provided when executing the command

    The subclass must be declared in the corresponding section of main.COMMAND_GROUPS.

    If the command may produce the result in a programmatic-friendly format, it
    should call the 'include_format_option' method to properly affect the parser and
    then emit only one message with the result of the 'format_content' method.
    """

    needs_config = False

    def format_content(self, fmt, content):
        """Format the content."""
        if fmt == JSON_FORMAT:
            return json.dumps(content, indent=4)
        raise ValueError("Specified format not supported.")

    def include_format_option(self, parser):
        """Add the 'format' option to this parser."""
        parser.add_argument(
            "--format",
            choices=[JSON_FORMAT],
            help="Produce the result formatted as a JSON string",
        )
