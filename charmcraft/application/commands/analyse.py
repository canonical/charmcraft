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
"""Command for analysing a charm."""
import argparse
import json
import pathlib
from collections.abc import Container

from craft_cli import emit
from pydantic.json import pydantic_encoder

from charmcraft import errors, linters
from charmcraft.application.commands import base
from charmcraft.models import lint

OVERVIEW = """\
Analyze a charm.

Report the attributes and lint results directly in the terminal. Use
`--force` to run even those configured to be ignored.
"""


class Analyse(base.CharmcraftCommand):
    """Run analysis on a built charm."""

    name = "analyse"
    help_msg = "Analyse a charm"
    overview = OVERVIEW
    format_option = True

    def fill_parser(self, parser) -> None:
        """Add command-specific parameters."""
        super().fill_parser(parser)
        parser.add_argument(
            "--force",
            action="store_true",
            # For backwards compatibility. This command doesn't ignore suppressed linters from charmcraft.yaml.
            help=argparse.SUPPRESS,
        )
        parser.add_argument("--ignore", help="Linters to ignore (comma separated)")
        parser.add_argument("filepath", type=pathlib.Path, help="The charm to analyse")

    def run(self, parsed_args: argparse.Namespace) -> int:
        """Run the 'analyse' command."""
        if not parsed_args.filepath.exists():
            raise errors.CraftError(
                f"Charm file not found: {str(parsed_args.filepath)}",
                retcode=1,
                reportable=False,
                logpath_report=False,
            )

        ignore = parsed_args.ignore.split(",") if parsed_args.ignore else []
        if parsed_args.format:
            return self._run_formatted(parsed_args.filepath, ignore=ignore)
        return self._run_streaming(parsed_args.filepath, ignore=ignore)

    def _run_formatted(self, filepath: pathlib.Path, *, ignore=Container[str]) -> int:
        """Run the command, formatting the output into JSON or similar at the end."""
        results = list(self._services.analysis.lint_file(filepath))
        emit.message(json.dumps(results, indent=4, default=pydantic_encoder))
        return max(r.level for r in results).return_code

    def _run_streaming(self, filepath: pathlib.Path, *, ignore=Container[str]) -> int:
        """Run the command, printing linter results as we get them."""
        max_level = lint.ResultLevel.OK
        with emit.progress_bar(
            f"Linting {filepath.name}...", total=len(linters.CHECKERS)
        ) as progress:
            for result in self._services.analysis.lint_file(
                filepath, ignore=ignore, include_ignored=False
            ):
                emit.progress(str(result), permanent=True)
                max_level = max(result.level, max_level)
                progress.advance(1)

        return max_level.return_code


class Analyze(Analyse):
    """Analyse, but like a cowboy.

    US English synonym for analyse command. Hidden from the help text because
    there should be only one form of the command visible.
    """

    name = "analyze"
    hidden = True
