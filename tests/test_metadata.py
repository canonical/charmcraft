# Copyright 2020-2022 Canonical Ltd.
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

import re
from textwrap import dedent

import pytest
from craft_cli import CraftError

from charmcraft.metadata import parse_metadata_yaml, read_metadata_yaml


# tests for parsing metadata


def test_parse_metadata_yaml_complete(tmp_path):
    """Example of parsing with all the optional attributes."""
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(
        """
        name: test-name
        summary: Test summary
        description: Lot of text.
    """
    )

    metadata = parse_metadata_yaml(tmp_path)

    assert metadata.name == "test-name"
    assert metadata.summary == "Test summary"
    assert metadata.description == "Lot of text."


@pytest.mark.parametrize("name", ["name1", "my-charm-foo"])
def test_parse_metadata_yaml_valid_names(tmp_path, name):
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(f"name: {name}")

    metadata = parse_metadata_yaml(tmp_path)

    assert metadata.name == name


@pytest.mark.parametrize("name", [1, "false", "[]"])
def test_parse_metadata_yaml_error_invalid_names(tmp_path, name):
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(f"name: {name}")

    expected_error_msg = dedent(
        """\
        Bad metadata.yaml content:
        - string type expected in field 'name'"""
    )
    with pytest.raises(CraftError, match=re.escape(expected_error_msg)):
        parse_metadata_yaml(tmp_path)


def test_parse_metadata_yaml_error_missing(tmp_path):
    msg = re.escape(
        "Cannot read the metadata.yaml file: FileNotFoundError(2, 'No such file or directory')"
    )
    with pytest.raises(CraftError, match=msg):
        parse_metadata_yaml(tmp_path)


# tests for reading metadata raw content


def test_read_metadata_yaml_complete(tmp_path):
    """Example of parsing with all the optional attributes."""
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text(
        """
        name: test-name
        summary: Test summary
        description: Text.
    """
    )

    metadata = read_metadata_yaml(tmp_path)
    assert metadata == {"name": "test-name", "summary": "Test summary", "description": "Text."}


def test_read_metadata_yaml_error_invalid(tmp_path):
    """Open a metadata.yaml that would fail verification."""
    metadata_file = tmp_path / "metadata.yaml"
    metadata_file.write_text("- whatever")
    metadata = read_metadata_yaml(tmp_path)
    assert metadata == ["whatever"]


def test_read_metadata_yaml_error_missing(tmp_path):
    """Do not hide the file not being accesible."""
    with pytest.raises(OSError):
        read_metadata_yaml(tmp_path)
