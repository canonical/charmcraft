# Copyright 2020 Canonical Ltd.
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
# For further info, check https://github.com/canonical/charm


import logging

from charm.cmdbase import BaseCommand

logger = logging.getLogger(__name__)


class VersionCommand(BaseCommand):
    """Show the version."""
    name = 'version'
    help_msg = "show the version"

    def run(self, parsed_args):
        """Run the command."""
        # XXX: we need to define how we want to store the project version (in config/file/etc.)
        version = '0.0.1'
        logger.info('Version: %s', version)


# XXX: the following commands are left here as an example of different commands... but in
# reality new commands will have new files for them


class CommandExampleDebug(BaseCommand):
    """Just an example."""

    name = 'example-debug'
    help_msg = "show msg in debug"

    def fill_parser(self, parser):
        parser.add_argument('foo')
        parser.add_argument('--bar', action='store_true', help="To use this command in a bar")

    def run(self, parsed_args):
        logger.debug(
            "Example showing log in DEBUG: foo=%s bar=%s", parsed_args.foo, parsed_args.bar)


class CommandExampleError(BaseCommand):
    """Just an example."""

    name = 'example-error'
    help_msg = "show msg in error"

    def run(self, parsed_args):
        logger.error("Example showing log in ERROR.")
