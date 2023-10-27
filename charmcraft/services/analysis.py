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

"""Service class for packing."""
from __future__ import annotations

import pathlib
import tempfile
import zipfile
from typing import Container, Iterator, Tuple

import craft_application
from craft_cli import emit

from charmcraft import linters, models
from charmcraft.linters import CHECKERS
from charmcraft.models.lint import CheckResult, CheckType, LintResult


class AnalysisService(craft_application.AppService):
    """Business logic for creating packages."""

    _project: models.CharmcraftProject  # type: ignore[assignment]

    def __init__(  # (too many arguments)
        self, app: craft_application.AppMetadata, services: craft_application.ServiceFactory
    ) -> None:
        super().__init__(app, services)

    def gen_results(self, override_ignore: bool = False) -> Iterator[CheckResult]:
        """Generate linting results.

        :param override_ignore: If True, all linters are run, even if ignored in charmcraft.yaml
        :yields: A CheckResult for each linter result.
        """
        if self._project.analysis:
            ignore_attributes = self._project.analysis.ignore.attributes
            ignore_linters = self._project.analysis.ignore.linters
        else:
            ignore_attributes = ignore_linters = []  # type: ignore[assignment]
        for check_class in CHECKERS:
            is_attr = check_class.check_type == CheckType.ATTRIBUTE
            is_lint = check_class.check_type == CheckType.LINT
            ignored_attr = is_attr and check_class.name in ignore_attributes
            ignored_linter = is_lint and check_class.name in ignore_linters
            if not override_ignore and (ignored_attr or ignored_linter):
                check_result = CheckResult(
                    check_type=check_class.check_type,
                    name=check_class.name,
                    result=LintResult.IGNORED,
                    url=check_class.url,
                    text="",
                )
            else:
                checker = check_class()
                try:
                    result = checker.run(self._project_dir)
                except Exception:
                    result = LintResult.UNKNOWN if is_attr else LintResult.FATAL
                check_result = CheckResult(
                    check_type=checker.check_type,
                    name=checker.name,
                    url=checker.url,
                    text=checker.text,
                    result=result,
                )
            if is_attr:
                self._results.setdefault(CheckType.ATTRIBUTE, []).append(check_result)
            else:
                self._results.setdefault(check_result.result, []).append(check_result)
            yield check_result
        self._lint_run = True

    def emit_results(self, override_ignore: bool = False) -> list[CheckResult]:
        """Print the linter results as they're generated and return them as a list."""
        results: list[CheckResult] = []
        for result in self.gen_results(override_ignore):
            results.append(result)
            if result.result == LintResult.IGNORED:
                continue
            if result.check_type == CheckType.ATTRIBUTE:
                emit.verbose(
                    f"Check result: {result.name} [{result.check_type.value}] {result.result} "
                    f"({result.text}; see more at {result.url}."
                )
                continue
            if result.result == LintResult.ERROR:
                headline = "ERROR"
            elif result.result == LintResult.WARNING:
                headline = "WARNING"
            else:
                continue
            emit.progress(
                f"{headline}: {result.name}: {result.text} ({result.url})", permanent=True
            )

        return results

    def lint_directory(
        self, path: pathlib.Path, *, ignore: Container[str] = (), include_ignored: bool = True
    ) -> Iterator[CheckResult]:
        """Lint an unpacked charm in the given directory."""
        # TODO: Get the stuff to ignore
        for checker, run in self._gen_checkers(ignore=ignore):
            if run:
                yield checker.get_result(path)
            elif include_ignored:
                yield checker.get_ignore_result()

    def lint_file(
        self, path: pathlib.Path, *, ignore: Container[str] = (), include_ignored: bool = True
    ) -> Iterator[CheckResult]:
        """Lint a packed charm.

        :param path: The path to the file
        :param ignore: a list of checker names to ignore.
        :param include_ignored: Whether to include ignored values in the output

        raises: FileNotFoundError if the file doesn't exist
        """
        path = path.resolve(strict=True)

        with tempfile.TemporaryDirectory(prefix=f"charmcraft_{path.name}_") as directory:
            directory_path = pathlib.Path(directory)
            with zipfile.ZipFile(path) as zip_file:
                zip_file.extractall(directory_path)
                # fix permissions as extractall does not keep them (see https://bugs.python.org/issue15795)
                for name in zip_file.namelist():
                    info = zip_file.getinfo(name)
                    inside_zip_mode = info.external_attr >> 16
                    extracted_file = directory_path / name
                    current_mode = extracted_file.stat().st_mode
                    if current_mode != inside_zip_mode:
                        extracted_file.chmod(inside_zip_mode)
            yield from self.lint_directory(directory_path, ignore=ignore, include_ignored=include_ignored)

    @staticmethod
    def _gen_checkers(ignore: Container[str]) -> Iterator[Tuple[linters.BaseChecker, bool]]:
        """Generate the checker classes to run, in their correct order."""
        for cls in linters.CHECKERS:
            run_linter = cls.name not in ignore
            yield cls(), run_linter
