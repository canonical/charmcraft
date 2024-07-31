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

import pydantic
import pytest
from craft_cli import CraftError

from charmcraft import const
from charmcraft.metafiles.metadata import read_metadata_yaml


# tests for reading metadata raw content


def test_read_metadata_yaml_complete(tmp_path):
    """Example of parsing with all the optional attributes."""
    metadata_file = tmp_path / const.METADATA_FILENAME
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
    metadata_file = tmp_path / const.METADATA_FILENAME
    metadata_file.write_text("- whatever")
    metadata = read_metadata_yaml(tmp_path)
    assert metadata == ["whatever"]


def test_read_metadata_yaml_error_missing(tmp_path):
    """Do not hide the file not being accessible."""
    with pytest.raises(OSError):
        read_metadata_yaml(tmp_path)
