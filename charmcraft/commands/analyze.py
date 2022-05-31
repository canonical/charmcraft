# Copyright 2021-2022 Canonical Ltd.
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

"""Infrastructure for the 'analyze' command."""

import pathlib
import tempfile
import textwrap
import zipfile

from craft_cli import emit, CraftError

from charmcraft import linters
from charmcraft.cmdbase import BaseCommand
from charmcraft.utils import useful_filepath


class AnalyzeCommand(BaseCommand):
    """Analyze a charm."""

    name = "analyze"
    help_msg = "Analyze a charm"
    overview = textwrap.dedent(
        """
        Analyze a charm.

        Report the attributes and lint results directly in the terminal. Use
        `--force` to run even those configured to be ignored.
    """
    )
    needs_config = False  # optional until we fully support charms here

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        self.include_format_option(parser)
        parser.add_argument("filepath", type=useful_filepath, help="The charm to analyze")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force to run all checks, even those set to ignore in the configuration",
        )

    def _unzip_charm(self, filepath: pathlib.Path) -> pathlib.Path:
        """Extract the charm content to a temp directory."""
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        try:
            zf = zipfile.ZipFile(str(filepath))
            zf.extractall(path=str(tmpdir))
        except Exception as exc:
            raise CraftError(f"Cannot open charm file {str(filepath)!r}: {exc!r}.")

        # fix permissions as extractall does not keep them (see https://bugs.python.org/issue15795)
        for name in zf.namelist():
            info = zf.getinfo(name)
            inside_zip_mode = info.external_attr >> 16
            extracted_file = tmpdir / name
            current_mode = extracted_file.stat().st_mode
            if current_mode != inside_zip_mode:
                extracted_file.chmod(inside_zip_mode)

        return tmpdir

    def run(self, parsed_args):
        """Run the command."""
        tmpdir = self._unzip_charm(parsed_args.filepath)

        # run the analyzer
        override_ignore_config = bool(parsed_args.force)
        linting_results = linters.analyze(
            self.config,
            tmpdir,
            override_ignore_config=override_ignore_config,
        )

        # if format is json almost no further processing is needed
        if parsed_args.format:
            info = [
                {
                    "name": r.name,
                    "result": r.result,
                    "url": r.url,
                    "type": r.check_type,
                }
                for r in linting_results
            ]
            emit.message(self.format_content(parsed_args.format, info))
            return

        # group by attributes and lint outcomes (discarding ignored ones)
        grouped = {}
        for result in linting_results:
            if result.check_type == linters.CheckType.attribute:
                group_key = linters.CheckType.attribute
                result_info = result.result
            else:
                # linters
                group_key = result.result
                if result.result == linters.OK:
                    result_info = "no issues found"
                elif result.result in (linters.FATAL, linters.IGNORED):
                    result_info = None
                else:
                    result_info = result.text
            grouped.setdefault(group_key, []).append((result, result_info))

        # present the results
        titles = [
            ("Attributes", linters.CheckType.attribute),
            ("Lint Ignored", linters.IGNORED),
            ("Lint Warnings", linters.WARNINGS),
            ("Lint Errors", linters.ERRORS),
            ("Lint Fatal", linters.FATAL),
            ("Lint OK", linters.OK),
        ]
        for title, key in titles:
            results = grouped.get(key)
            if results is not None:
                emit.message(f"{title}:")
                for result, result_info in results:
                    if result_info:
                        emit.message(f"- {result.name}: { result_info} ({result.url})")
                    else:
                        emit.message(f"- {result.name} ({result.url})")

        # the return code depends on the presence of different issues
        if linters.FATAL in grouped:
            retcode = 1
        elif linters.ERRORS in grouped:
            retcode = 2
        elif linters.WARNINGS in grouped:
            retcode = 3
        else:
            retcode = 0

        return retcode
