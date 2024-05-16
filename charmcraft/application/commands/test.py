# Copyright 2024 Canonical Ltd.
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

"""Infrastructure for the 'test' command."""
import argparse
import os
import subprocess
import sys

from craft_cli import CraftError, emit

from charmcraft import env
from charmcraft.application.commands import base

_overview = """
Run charm tests in different back-ends.

This command will run charm test suites using the spread tool. For further
information, see the spread documentation: https://github.com/snapcore/spread
"""


class TestCommand(base.CharmcraftCommand):
    """Initialize a directory to be a charm project."""

    name = "test"
    help_msg = "Execute charm test suites"
    overview = _overview
    common = True

    def fill_parser(self, parser):
        """Specify command's specific parameters."""
        parser.add_argument(
            "spread_args",
            metavar="spread arguments",
            nargs=argparse.REMAINDER,
            help="Arguments to spread",
        )

        # XXX: Arguments to the test command are passed directly to spread.
        #      Inject separator in the argument to avoid parsing test command
        #      arguments. We should implement better support for this case
        #      in craft-application.
        idx = sys.argv.index("test") + 1
        sys.argv = [*sys.argv[:idx], "--", *sys.argv[idx:]]

    def run(self, parsed_args: argparse.Namespace):
        """Execute command's actual functionality."""
        # If running on github and no arguments are specified, use the
        # github-ci backend.
        spread_args = parsed_args.spread_args
        if len(spread_args) > 0 and spread_args[0] == "--":
            spread_args = spread_args[1:]

        if len(spread_args) == 0 and os.environ.get("GITHUB_RUN_ID"):
            spread_args = ["github-ci"]

        if env.is_charmcraft_running_from_snap():
            cmd = f"{os.environ['SNAP']}/bin/spread"
        else:
            cmd = "spread"

        try:
            with emit.pause():
                subprocess.run([cmd, *spread_args], check=True)
        except subprocess.CalledProcessError as err:
            raise CraftError(f"test error: {err}")
