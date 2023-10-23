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
from typing import Iterator, cast

import craft_application
from craft_cli import emit

from charmcraft import models
from charmcraft.errors import LintingError
from charmcraft.linters import CHECKERS
from charmcraft.models.lint import CheckResult, CheckType, LintResult
from charmcraft.models.project import CharmcraftProject


class AnalysisService(craft_application.BaseService):
    """Business logic for creating packages."""

    _project: models.CharmcraftProject  # type: ignore[assignment]

    def __init__(  # (too many arguments)
        self,
        app: craft_application.AppMetadata,
        project: CharmcraftProject,
        services: craft_application.ServiceFactory,
        *,
        project_dir: pathlib.Path,
    ) -> None:
        super().__init__(app, cast(craft_application.models.Project, project), services)
        self._project_dir = project_dir.resolve(strict=True)
        self._results: dict[str, list[CheckResult]] = {}
        self._lint_run = False

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
            if result.result == LintResult.ERRORS:
                headline = "ERROR"
            elif result.result == LintResult.WARNINGS:
                headline = "WARNING"
            else:
                continue
            emit.progress(
                f"{headline}: {result.name}: {result.text} ({result.url})", permanent=True
            )

        return results

    def check_success(self) -> None:
        """Check whether all linters succeeded.

        Returns: None if all linters succeeded
        Raises: LintingError if any linters errored.
        """
        if not self._lint_run:
            for _ in self.gen_results():
                pass
        if LintResult.ERRORS in self._results:
            raise LintingError(
                self._results[LintResult.ERRORS], self._results.get(LintResult.WARNINGS, [])
            )

    def get_result_groups(self):
        """Get a dictionary of grouped results."""
        if not self._lint_run:
            for _ in self.gen_results():
                pass
        return self._results
