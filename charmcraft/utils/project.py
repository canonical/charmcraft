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
"""Charm project related utilities."""
import itertools
import os
import pathlib
import sys
from collections import defaultdict
from collections.abc import Container

from craft_cli import emit
from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined

from charmcraft import const
from charmcraft.errors import DuplicateCharmsError, InvalidCharmPathError
from charmcraft.utils.yaml import load_yaml


def find_charm_sources(
    base_path: pathlib.Path, charm_names: Container[str]
) -> dict[str, pathlib.Path]:
    """Find all charm directories matching the given names under a base path.

    :param base_path: The base directory under which to look.
    :param charm_names: A container with charm names to find.
    :returns: A dictionary mapping charm names to their paths.
    :raises: DuplicateCharmsError if a charm is found in multiple directories.
    """
    duplicate_charms = defaultdict(list)
    charm_paths: dict[str, pathlib.Path] = {}
    outer_potential_paths = itertools.chain(
        (p.parent.resolve() for p in base_path.glob("charms/*/metadata.yaml")),
        (p.parent.resolve() for p in base_path.glob("operators/*/metadata.yaml")),
        (p.parent.resolve() for p in base_path.glob("*/metadata.yaml")),
    )
    potential_paths = filter(
        lambda p: (p / const.CHARMCRAFT_FILENAME).exists(), outer_potential_paths
    )
    for path in potential_paths:
        if path in charm_paths.values():  # Symlinks can cause ignorable duplicate paths.
            continue
        try:
            charm_name = get_charm_name_from_path(path)
        except InvalidCharmPathError:
            continue
        if charm_name not in charm_names:  # We only care if the charm is listed for finding
            continue
        if charm_name != path.name:
            emit.verbose(f"Charm {charm_name!r} found in non-matching path {path}")
            continue
        if charm_name in charm_paths:
            duplicate_charms[charm_name].append(path)
        else:
            charm_paths[charm_name] = path
    if duplicate_charms:
        raise DuplicateCharmsError(duplicate_charms)
    return charm_paths


def get_charm_name_from_path(path: pathlib.Path) -> str:
    """Get a charm's name from a given path.

    :param path: The path to investigate.
    :returns: The name of the charm in this path
    :raises: InvalidCharmPathError if the path given is not a valid charm source.
    """
    charmcraft_yaml = load_yaml(path / const.CHARMCRAFT_FILENAME)
    if charmcraft_yaml is None or charmcraft_yaml.get("type") != "charm":
        raise InvalidCharmPathError(path)
    metadata_yaml = load_yaml(path / const.METADATA_FILENAME)
    if metadata_yaml is None or "name" not in metadata_yaml:
        raise InvalidCharmPathError(path)
    return metadata_yaml["name"]


def get_templates_environment(templates_dir):
    """Create and return a Jinja environment to deal with the templates."""
    templates_dir = os.path.join("templates", templates_dir)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as PyInstaller bundle. For more information:
        # https://pyinstaller.readthedocs.io/en/stable/runtime-information.html
        # In this scenario we need to load from the data location that is unpacked
        # into the temporary directory at runtime (sys._MEIPASS).
        emit.debug(f"Bundle directory: {sys._MEIPASS}")
        loader = FileSystemLoader(os.path.join(sys._MEIPASS, templates_dir))
    else:
        loader = PackageLoader("charmcraft", templates_dir)

    return Environment(
        loader=loader,
        autoescape=False,  # no need to escape things here :-)
        keep_trailing_newline=True,  # they're not text files if they don't end in newline!
        optimized=False,  # optimization doesn't make sense for one-offs
        undefined=StrictUndefined,
    )  # fail on undefined
