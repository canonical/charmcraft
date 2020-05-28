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

from charmcraft.cmdbase import BaseCommand

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
