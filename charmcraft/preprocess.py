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
"""Pre-processing functions for charmcraft projects.

These functions are called from the Application class's `_extra_yaml_transform`
to do pre-processing on a charmcraft.yaml file before applying extensions.
"""
import pathlib
from typing import Any

from craft_application import util

from charmcraft import const, errors, utils


def add_default_parts(yaml_data: dict[str, Any]) -> None:
    """Apply the expected default parts to a project if it doesn't contain any.

    :param yaml_data: The raw YAML dictionary of the project.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    if (yaml_data.get("type")) != "bundle":
        return
    parts = yaml_data.setdefault("parts", {})
    if parts:  # Only operate if there aren't any parts declared.
        return

    parts["bundle"] = {"plugin": "bundle", "source": "."}


def add_metadata(project_dir: pathlib.Path, yaml_data: dict[str, Any]) -> None:
    """Add the contents of metadata.yaml to a project data structure.

    :param project_dir: The directory containing charmcraft.yaml and possibly metadata.yaml.
    :param yaml_data: The current project data from charmcraft.yaml.
    """
    metadata_path = pathlib.Path(project_dir / "metadata.yaml")
    if not metadata_path.exists():
        return

    with metadata_path.open() as file:
        metadata_yaml = util.safe_yaml_load(file)
    if not isinstance(metadata_yaml, dict):
        raise errors.CraftError(
            "Invalid file: 'metadata.yaml'",
            resolution="Ensure metadata.yaml meets the juju metadata.yaml specification.",
            docs_url="https://juju.is/docs/sdk/metadata-yaml",
            retcode=65,  # Data error, per sysexits.h
        )
    duplicate_fields = []
    for field in const.METADATA_YAML_MIGRATE_FIELDS:
        if field in yaml_data and field in metadata_yaml:
            duplicate_fields.append(field)
        yaml_data.setdefault(field, metadata_yaml.get(field))
    if duplicate_fields:
        raise errors.CraftError(
            "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
            details=f"Duplicate fields: {utils.humanize_list(duplicate_fields, 'and')}",
            resolution="Remove the duplicate fields from metadata.yaml.",
            retcode=65,  # Data error. per sysexits.h
        )


def add_bundle_snippet(project_dir: pathlib.Path, yaml_data: dict[str, Any]):
    """Add metadata from bundle.yaml to a bundle.

    :param yaml_data: The raw YAML dictionary of the project.
    :param project_dir: The Path to the directory containing charmcraft.yaml and bundle.yaml.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    if yaml_data.get("type") != "bundle":
        return

    bundle_file = project_dir / const.BUNDLE_FILENAME
    if not bundle_file.is_file():
        raise errors.CraftError(
            f"Missing 'bundle.yaml' file: {str(bundle_file)!r}",
            resolution="Create a 'bundle.yaml' file in the same directory as 'charmcraft.yaml'.",
            docs_url="https://juju.is/docs/sdk/create-a-charm-bundle",
            reportable=False,
            retcode=66,  # EX_NOINPUT from sysexits.h
        )

    with bundle_file.open() as bf:
        bundle = util.safe_yaml_load(bf)
    if not isinstance(bundle, dict):
        raise errors.CraftError(
            "Incorrectly formatted 'bundle.yaml' file",
            resolution="Ensure 'bundle.yaml' matches the Juju 'bundle.yaml' format.",
            docs_url="https://juju.is/docs/sdk/charm-bundles",
            reportable=False,
            retcode=65,  # EX_DATAERR from sysexits.h
        )
    yaml_data["bundle"] = bundle
