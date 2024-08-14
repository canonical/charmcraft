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
"""Tests for project pre-processing functions."""
import pathlib
import textwrap

import pytest

from charmcraft import const, errors, preprocess

BASIC_BUNDLE = {"type": "bundle", "parts": {"bundle": {"plugin": "bundle", "source": "."}}}
BASIC_CHARM = {"type": "charm", "parts": {"charm": {"plugin": "charm", "source": "."}}}
BASIC_BASES_CHARM = {**BASIC_CHARM, "bases": [{"name": "ubuntu", "channel": "22.04"}]}


@pytest.mark.parametrize(
    ("yaml_data", "expected"),
    [
        pytest.param({}, {}, id="no-type"),
        pytest.param({"type": "bundle"}, BASIC_BUNDLE, id="empty-bundle"),
        pytest.param(BASIC_BUNDLE.copy(), BASIC_BUNDLE, id="prefilled-bundle"),
        pytest.param(
            {"type": "charm", "bases": []},
            {"type": "charm", "bases": [], "parts": {"charm": {"plugin": "charm", "source": "."}}},
            id="empty-charm",
        ),
        pytest.param(BASIC_CHARM.copy(), BASIC_CHARM, id="basic-charm"),
    ],
)
def test_add_default_parts_correct(yaml_data, expected):
    preprocess.add_default_parts(yaml_data)

    assert yaml_data == expected


@pytest.mark.parametrize(
    ("yaml_data", "metadata_yaml", "expected"),
    [
        pytest.param({}, None, {}, id="nonexistent"),
        pytest.param({}, "{}", {"name": None, "summary": None, "description": None}, id="empty"),
        pytest.param(
            {"name": "my-charm"},
            "summary: a charm",
            {"name": "my-charm", "summary": "a charm", "description": None},
            id="merge",
        ),
        pytest.param(
            {},
            "name: my-charm",
            {"name": "my-charm", "summary": None, "description": None},
            id="only-from-metadata",
        ),
    ],
)
def test_add_metadata_success(fs, yaml_data, metadata_yaml, expected):
    if metadata_yaml is not None:
        fs.create_file("/project/metadata.yaml", contents=metadata_yaml)

    preprocess.add_metadata(pathlib.Path("/project"), yaml_data)

    assert yaml_data == expected


@pytest.mark.parametrize(
    ("yaml_data", "metadata_yaml", "message"),
    [
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
            },
            "",
            "Invalid file: 'metadata.yaml'",
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
            },
            textwrap.dedent(
                """\
                name: test-charm
                summary: A test charm
                description: A charm for testing!"""
            ),
            "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
        ),
    ],
)
def test_extra_yaml_transform_failure(fs, yaml_data, metadata_yaml, message):
    fs.create_file("metadata.yaml", contents=metadata_yaml)

    with pytest.raises(errors.CraftError) as exc_info:
        preprocess.add_metadata(pathlib.Path("/"), yaml_data)

    assert exc_info.value.args[0] == message


@pytest.mark.parametrize(
    ("yaml_data", "bundle_yaml", "expected"),
    [
        pytest.param({}, "", {}, id="non-bundle"),
        pytest.param(
            {"type": "bundle"}, "{}", {"type": "bundle", "bundle": {}}, id="empty-bundle"
        ),
    ],
)
def test_add_bundle_snippet_success(fs, yaml_data, bundle_yaml, expected):
    project_dir = pathlib.Path("project")
    fs.create_file(project_dir / const.BUNDLE_FILENAME, contents=bundle_yaml)

    preprocess.add_bundle_snippet(project_dir, yaml_data)

    assert yaml_data == expected


def test_add_bundle_snippet_no_file(fs):
    fs.create_dir("project")

    with pytest.raises(
        errors.CraftError, match="^Missing 'bundle.yaml' file: '.*bundle.yaml'"
    ) as exc_info:
        preprocess.add_bundle_snippet(pathlib.Path("/project"), {"type": "bundle"})

    assert exc_info.value.retcode == 66


@pytest.mark.parametrize("contents", ["", "A string", "0", "[]"])
def test_add_bundle_snippet_invalid_file(fs, contents):
    fs.create_file("project/bundle.yaml", contents=contents)

    with pytest.raises(
        errors.CraftError, match="Incorrectly formatted 'bundle.yaml' file"
    ) as exc_info:
        preprocess.add_bundle_snippet(pathlib.Path("project"), {"type": "bundle"})

    assert exc_info.value.retcode == 65


@pytest.mark.parametrize(
    ("yaml_data", "config_yaml", "expected"),
    [
        ({}, "{}", {"config": {}}),
        ({}, "options:\n boop:\n  type: int", {"config": {"options": {"boop": {"type": "int"}}}}),
    ],
)
def test_add_config_success(fs, yaml_data, config_yaml, expected):
    project_dir = pathlib.Path("project")
    fs.create_file(project_dir / const.JUJU_CONFIG_FILENAME, contents=config_yaml)

    preprocess.add_config(project_dir, yaml_data)

    assert yaml_data == expected


@pytest.mark.parametrize(
    ("yaml_data", "actions_yaml", "expected"),
    [
        ({}, "", {}),
        ({}, "{}", {}),
        (
            {},
            "boop:\n description: Boop in the snoot",
            {"actions": {"boop": {"description": "Boop in the snoot"}}},
        ),
    ],
)
def test_add_actions_success(fs, yaml_data, actions_yaml, expected):
    project_dir = pathlib.Path("project")
    fs.create_file(project_dir / const.JUJU_ACTIONS_FILENAME, contents=actions_yaml)

    preprocess.add_actions(project_dir, yaml_data)

    assert yaml_data == expected
