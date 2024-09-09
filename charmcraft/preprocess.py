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

from craft_application import errors, util

from charmcraft import const, utils


def add_default_parts(yaml_data: dict[str, Any]) -> None:
    """Apply the expected default parts to a project if it doesn't contain any.

    :param yaml_data: The raw YAML dictionary of the project.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    if yaml_data.get("parts"):  # Only operate if there aren't any parts.
        return

    if yaml_data.get("type") == "bundle":
        yaml_data["parts"] = {"bundle": {"plugin": "bundle", "source": "."}}
    elif yaml_data.get("type") == "charm":
        # Only for backwards compatibility for bases charms.
        # Platforms charms expect parts to be explicit.
        if "bases" in yaml_data:
            yaml_data["parts"] = {"charm": {"plugin": "charm", "source": "."}}


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
        raise errors.CraftValidationError(
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
        raise errors.CraftValidationError(
            "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
            details=f"Duplicate fields: {utils.humanize_list(duplicate_fields, 'and')}",
            resolution="Remove the duplicate fields from metadata.yaml.",
            retcode=65,  # Data error. per sysexits.h
        )


def add_bundle_snippet(project_dir: pathlib.Path, yaml_data: dict[str, Any]) -> None:
    """Add metadata from bundle.yaml to a bundle.

    :param yaml_data: The raw YAML dictionary of the project.
    :param project_dir: The Path to the directory containing charmcraft.yaml and bundle.yaml.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    if yaml_data.get("type") != "bundle":
        return

    bundle_file = project_dir / const.BUNDLE_FILENAME
    if not bundle_file.is_file():
        raise errors.CraftValidationError(
            f"Missing 'bundle.yaml' file: {str(bundle_file)!r}",
            resolution="Create a 'bundle.yaml' file in the same directory as 'charmcraft.yaml'.",
            docs_url="https://juju.is/docs/sdk/create-a-charm-bundle",
            reportable=False,
            retcode=66,  # EX_NOINPUT from sysexits.h
        )

    with bundle_file.open() as bf:
        bundle = util.safe_yaml_load(bf)
    if not isinstance(bundle, dict):
        raise errors.CraftValidationError(
            "Incorrectly formatted 'bundle.yaml' file",
            resolution="Ensure 'bundle.yaml' matches the Juju 'bundle.yaml' format.",
            docs_url="https://juju.is/docs/sdk/charm-bundles",
            reportable=False,
            retcode=65,  # EX_DATAERR from sysexits.h
        )
    yaml_data["bundle"] = bundle


def add_config(project_dir: pathlib.Path, yaml_data: dict[str, Any]) -> None:
    """Add configuration options from config.yaml to existing YAML data.

    :param project_dir: The Path to the directory containing charmcraft.yaml
    :param yaml_data: The raw YAML dictionary of the project.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    config_file = project_dir / const.JUJU_CONFIG_FILENAME
    if not config_file.exists():
        return

    if "config" in yaml_data:
        raise errors.CraftValidationError(
            f"Cannot specify 'config' section in 'charmcraft.yaml' when {const.JUJU_CONFIG_FILENAME!r} exists",
            resolution=f"Move all data from {const.JUJU_CONFIG_FILENAME!r} to the 'config' section in 'charmcraft.yaml'",
            docs_url="https://juju.is/docs/sdk/charmcraft-yaml",
            retcode=65,  # Data error, per sysexits.h
        )

    with config_file.open() as f:
        yaml_data["config"] = util.safe_yaml_load(f)


def add_actions(project_dir: pathlib.Path, yaml_data: dict[str, Any]) -> None:
    """Add actions from actions.yaml to existing YAML data.

    :param project_dir: The Path to the directory containing charmcraft.yaml
    :param yaml_data: The raw YAML dictionary of the project.
    :returns: The same dictionary passed in, with necessary mutations.
    """
    actions_file = project_dir / const.JUJU_ACTIONS_FILENAME
    if not actions_file.exists():
        return

    if "actions" in yaml_data:
        raise errors.CraftValidationError(
            f"Cannot specify 'actions' section in 'charmcraft.yaml' when {const.JUJU_ACTIONS_FILENAME!r} exists",
            resolution=f"Move all data from {const.JUJU_ACTIONS_FILENAME!r} to the 'actions' section in 'charmcraft.yaml'",
            docs_url="https://juju.is/docs/sdk/charmcraft-yaml",
            retcode=65,  # Data error, per sysexits.h
        )
    with actions_file.open() as f:
        actions = util.safe_yaml_load(f)
    if actions and isinstance(actions, dict):
        yaml_data["actions"] = actions
