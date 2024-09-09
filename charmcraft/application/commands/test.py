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

    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        """Specify the parameters for this command."""
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--shell",
            action="store_true",
            help="Shell into the environment in lieu of the step to run.",
        )
        group.add_argument(
            "--shell-after",
            action="store_true",
            help="Shell into the environment after the step has run.",
        )

        parser.add_argument(
            "--debug",
            action="store_true",
            help="Shell into the environment if the build fails.",
        )

        parser.add_argument(
            "--list",
            action="store_true",
            help="Just show the list of jobs that would run.",
        )

        parser.add_argument(
            "spread_tasks",
            metavar="tasks",
            nargs=argparse.REMAINDER,
            help=(
                "Spread tasks to run, in backend:system:suite/task:variant "
                "format. All fields are optional."
            ),
        )

    def run(self, parsed_args: argparse.Namespace):
        """Execute command's actual functionality."""
        if env.is_charmcraft_running_from_snap():
            cmd = [f"{os.environ['SNAP']}/bin/spread"]
        else:
            cmd = ["spread"]

        for arg in ("shell", "shell-after", "debug", "list"):
            if vars(parsed_args).get(arg):
                cmd.append("-" + arg)

        # Choose the github-ci backend if running on GitHub, otherwise default
        # to multipass.
        spread_tasks = parsed_args.spread_tasks
        if len(spread_tasks) == 0:
            if os.environ.get("GITHUB_RUN_ID"):
                spread_tasks = ["github-ci"]
            else:
                spread_tasks = ["multipass"]

        try:
            with emit.pause():
                subprocess.run([*cmd, *spread_tasks], check=True)
        except subprocess.CalledProcessError as err:
            raise CraftError(f"test error: {err}")
