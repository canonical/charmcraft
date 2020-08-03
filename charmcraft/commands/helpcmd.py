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
# For further info, check https://github.com/canonical/charmcraft


import logging

from charmcraft import help
from charmcraft.cmdbase import BaseCommand

logger = logging.getLogger(__name__)

# FIXME: all untested
# FIXME: missing the --all option

class HelpCommand(BaseCommand):
    """Show the version."""
    name = 'help'
    help_msg = "Show these help messages."

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'command', type=str, nargs='?',
            help="the directory where the charm project is located, from where the build "
                 "is done; defaults to '.'")

    def run(self, parsed_args):
        """Run the command."""
        print("=========== h?", repr(parsed_args.command))
        #logger.info('Version: %s', __version__)
        # FIXME: implement
