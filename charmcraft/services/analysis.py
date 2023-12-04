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
from collections.abc import Container, Iterator

import craft_application

from charmcraft import errors, linters, models
from charmcraft.models.lint import CheckResult


class AnalysisService(craft_application.AppService):
    """Business logic for creating packages."""

    _project: models.CharmcraftProject  # type: ignore[assignment]

    def __init__(  # (too many arguments)
        self, app: craft_application.AppMetadata, services: craft_application.ServiceFactory
    ) -> None:
        super().__init__(app, services)

    def lint_directory(
        self, path: pathlib.Path, *, ignore: Container[str] = (), include_ignored: bool = True
    ) -> Iterator[CheckResult]:
        """Lint an unpacked charm in the given directory."""
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
            try:
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
            except zipfile.BadZipfile as exc:
                raise errors.CraftError(
                    f"Cannot open charm file '{path}': {exc.args[0]}",
                    resolution=f"Check the charm file at {path}",
                    reportable=False,
                )
            yield from self.lint_directory(
                directory_path, ignore=ignore, include_ignored=include_ignored
            )

    @staticmethod
    def _gen_checkers(ignore: Container[str]) -> Iterator[tuple[linters.BaseChecker, bool]]:
        """Generate the checker classes to run, in their correct order."""
        for cls in linters.CHECKERS:
            run_linter = cls.name not in ignore
            yield cls(), run_linter
