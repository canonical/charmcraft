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
"""Charmcraft error classes."""

import io
import pathlib
import shlex
import subprocess
import textwrap
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, cast

from craft_cli import CraftError
from typing_extensions import Self

if TYPE_CHECKING:
    from charmcraft.linters import CheckResult
else:
    CheckResult = "CheckResult"


class LibraryError(CraftError):
    """Errors related to charm libraries."""


class BadLibraryPathError(LibraryError):
    """Subclass to provide a specific error for a bad library path."""

    def __init__(self, path):
        super().__init__(
            f"Charm library path {path} must conform to lib/charms/<charm>/vN/<libname>.py"
        )


class BadLibraryNameError(LibraryError):
    """Subclass to provide a specific error for a bad library name."""

    def __init__(self, name):
        super().__init__(
            f"Charm library name {name!r} must conform to charms.<charm>.vN.<libname>"
        )


class InvalidCharmPathError(CraftError):
    """The path provided is not the source directory for a valid charm."""

    def __init__(self, path: pathlib.Path):
        super().__init__(
            f"Path does not contain source for a valid charm: {path}",
            resolution=(
                "Ensure the given path is a directory containing valid charmcraft.yaml "
                "and metadata.yaml files."
            ),
        )


class DuplicateCharmsError(CraftError):
    """Duplicate charms were found on disk for the same name.

    If source is True, this refers to charm sources. Otherwise, it refers to files.
    """

    _sources_resolution = (
        "Remove duplicate charms or specify directories with --include-charm. "
        "These can be seen with --verbosity=debug"
    )
    _files_resolution = (
        "Ensure each charm generates only one output file. "
        "Files can be seen with --verbosity=debug"
    )

    def __init__(
        self, charms: Mapping[str, Iterable[pathlib.Path]], source: bool = True
    ):
        import charmcraft.utils  # noqa: PLC0415  prevent circular imports

        charm_names = charmcraft.utils.humanize_list(charms.keys(), "and")
        super().__init__(
            f"Duplicate charms found: {charm_names}",
            details=self._format_details(charms),
            resolution=self._sources_resolution if source else self._files_resolution,
            logpath_report=False,
            reportable=False,
        )

    @staticmethod
    def _format_details(charms: Mapping[str, Iterable[pathlib.Path]]) -> str:
        # 6 is the length of "CHARM", the left side of the header.
        longest_name = max([max(len(k) for k in charms), 5])
        path_tree_line_format = "{name:>" + str(longest_name) + "} : {path}"
        details = io.StringIO()
        print("Charms with duplicate paths:", file=details)
        print(path_tree_line_format.format(name="CHARM", path="PATHS"), file=details)
        for charm, paths in charms.items():
            path_iter = iter(paths)
            print(
                path_tree_line_format.format(name=charm, path=next(path_iter)),
                file=details,
            )
            for path in path_iter:
                print(path_tree_line_format.format(name="", path=path), file=details)
        return details.getvalue()


class DependencyError(CraftError):
    """Errors related to dependencies."""


class MissingDependenciesError(DependencyError):
    """In strict dependencies mode, some dependencies are missing from requirements files."""

    def __init__(self, extra_dependencies: Iterable[str]):
        self.extra_dependencies = sorted(extra_dependencies)
        extra_deps_str = ", ".join(self.extra_dependencies)
        super().__init__(
            "Some dependencies were not included in requirements files.",
            details=f"Missing dependencies: {extra_deps_str}",
            resolution="Ensure all missing dependencies are included in a requirements file.",
            # TODO: Docs URL
            reportable=False,
        )


class ExtensionError(CraftError):
    """Error related to extension handling."""


class SkopeoError(CraftError):
    """Errors from when we call the skopeo executable."""

    @classmethod
    def from_subprocess(cls, error: subprocess.CalledProcessError) -> Self:
        """Convert a CalledProcessError into a Skopeo error."""
        if isinstance(error.stderr, str):
            stderr = error.stderr
        else:
            stderr_stream = cast(io.TextIOBase, error.stderr)
            stderr_stream.seek(io.SEEK_SET)
            stderr = stderr_stream.read()
        # Example stderr string:
        # time="2025-06-25T19:14:57-04:00" level=fatal msg="Error parsing image name \"docker://ghcr.io/canonical/spark-integration-hub:3.4-22.04_edge@sha256:0b9a40435440256b1c10020bd59d19e186ea68d8973fc8f2310010f9bd4e3459\": Docker references with both a tag and digest are currently not supported"
        # This lexes it and splits it into key/value pairs.
        error_parts = {
            key: value
            for key, _, value in (token.partition("=") for token in shlex.split(stderr))
        }
        if "msg" in error_parts:
            return cls(error_parts["msg"])
        else:
            return cls(
                "Unknown error from skopeo.",
                details=f"Error from skopeo. Return code {error.returncode}\nError text:\n"
                + textwrap.indent(error.stderr, "  "),
                resolution="Report a bug at https://github.com/canonical/charmcraft/issues",
            )
