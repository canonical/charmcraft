# Copyright 2020-2021 Canonical Ltd.
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

"""Infrastructure for the 'version' command."""

import logging

from charmcraft import __version__
from charmcraft.cmdbase import BaseCommand

logger = logging.getLogger(__name__)

_overview = """
Show charmcraft version.

The output has the following format: X.Y.Z[+N.gHASH[.dirty]]

Where:

- X, Y and Z are the major, minor and patch version numbers,
  upgraded when a release is done

- +N.gHASH is present if using charmcraft from the project (how many
  commits after last release, and last commit's hash)

- .dirty is present if the branch you're executing charmcraft from has
  modifications

Example: 0.3.1+40.g883455b.dirty
"""


class VersionCommand(BaseCommand):
    """Show the charmcraft version."""

    name = 'version'
    help_msg = "Show charmcraft version"
    overview = _overview
    common = True

    def run(self, parsed_args):
        """Run the command."""
        logger.info("%s", __version__)
