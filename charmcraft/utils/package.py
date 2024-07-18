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
"""Utilities related to Python packages."""
import pathlib
import re
import string
import subprocess
from collections.abc import Collection, Iterable

from charmcraft import errors

PACKAGE_LINE_REGEX = re.compile(r"^([A-Za-z0-9_.-]+)( *[~<>=!]==?)?")


def get_pypi_packages(*requirements: Iterable[str]) -> set[str]:
    """Get a set of pypi packages from requirements files.

    :param requirements: An iterable of strings for each requirement.
    :returns: A set of package names and their requirements (e.g. version numbers)
    """
    valid_package_start_chars = string.ascii_letters + string.digits
    packages = set()
    for req in requirements:
        for line in req:
            line = line.strip()
            if not line or line[0] not in valid_package_start_chars:
                continue
            if PACKAGE_LINE_REGEX.match(line):
                packages.add(line)

    return packages


def get_package_names(packages: Iterable[str]) -> set[str]:
    """Get just the names of packages from an iterable of package lines.

    :param packages: An iterable of package lines (e.g. ["abc==1.0.0", "def"])
    :returns: A set of package names only (e.g. {"abc", "def"})
    """
    names = set()
    for package in packages:
        if match := PACKAGE_LINE_REGEX.match(package):
            names.add(match.group(1))

    return names


def get_requirements_file_package_names(*requirements_files: pathlib.Path) -> set[str]:
    """Get all the package names from one or more requirements files as a single set."""
    packages = set()
    for file in requirements_files:
        packages |= get_package_names(
            get_pypi_packages(file.read_text().splitlines(keepends=False))
        )
    return packages


def exclude_packages(requirements: set[str], *, excluded: Collection[str]) -> set[str]:
    """Filter a set of requirements lines by a collection of package names.

    :param requirements: A set of requirements lines (e.g. {"abc==1.0.0", "def>=1.0"})
    :param excluded: A collection of package names (only) to exclude.
    :returns A filtered set of requirements, excluding the given packages.
    """
    exclusions = set()
    for requirement in requirements:
        if match := PACKAGE_LINE_REGEX.match(requirement):
            if match.group(1) in excluded:
                exclusions.add(requirement)

    return requirements - exclusions


def get_pip_command(
    prefix: Iterable[str],
    requirements_files: Collection[pathlib.Path],
    *,
    source_deps: Collection[str] = (),
    binary_deps: Collection[str] = (),
) -> list[str]:
    """Build a pip command based on requirements files and dependencies.

    :param prefix: The pip command and any earlier arguments.
    :param requirements_files: Paths to the requirements files to include.
    :param source_deps: Additional dependencies that can only be installed from source.
    :param binary_deps: Dependencies (including from requirements files) allowed for binary install.
    :returns: A full pip command line
    """
    charm_packages = get_pypi_packages(source_deps)
    binary_packages = get_pypi_packages(binary_deps)
    requirements_packages = get_requirements_file_package_names(*requirements_files)
    all_packages = charm_packages | binary_packages | requirements_packages
    non_requirements_packages = sorted(
        exclude_packages(
            set(source_deps) | set(binary_deps),
            excluded=get_package_names(requirements_packages),
        )
    )

    if not binary_packages:
        return [
            *prefix,
            "--no-binary=:all:",
            *(f"--requirement={path}" for path in requirements_files),
            *non_requirements_packages,
        ]

    source_only_packages = sorted(
        get_package_names(all_packages) - get_package_names(binary_packages)
    )
    no_binary = [f"--no-binary={','.join(source_only_packages)}"] if source_only_packages else ()

    return [
        *prefix,
        *no_binary,
        *(f"--requirement={path}" for path in requirements_files),
        *non_requirements_packages,
    ]


def get_pip_version(pip_cmd: str) -> tuple[int, ...]:
    """Get the version of pip available from a specific pip command."""
    result = subprocess.run([pip_cmd, "--version"], text=True, capture_output=True, check=True)
    version_data = result.stdout.split(" ")
    if len(version_data) < 2:
        raise ValueError("Unknown pip version")
    version_strings = version_data[1].split(".")
    try:
        return tuple(int(num) for num in version_strings)
    except ValueError:
        raise ValueError(f"Unknown pip version {version_data[1]}")


def validate_strict_dependencies(
    dependencies: Iterable[str], *other_packages: Collection[str]
) -> None:
    """Validate that a charm has an appropriate set of strict dependencies.

    :param dependencies: Packages that are included in known dependencies.
    :param other_packages: Packages from other sources, to ensure these packages are in the
        overall set of dependencies.
    """
    dependency_names = get_package_names(dependencies)

    extra_packages: set[str] = set()

    for package_set in other_packages:
        other_names = get_package_names(package_set)
        extra_packages |= other_names - dependency_names

    if extra_packages:
        raise errors.MissingDependenciesError(extra_packages)
