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

"""Tests for charm name related commands (code in store/name.py)."""
import pytest

from charmcraft.commands.store.name import get_name_from_metadata


class TestGetNameFromMetadata:
    """Tests for get_name_from_metadata"""

    @pytest.fixture(autouse=True)
    def charm_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        yield tmp_path

    @pytest.mark.parametrize(
        "name_line,name",
        [
            pytest.param(b"name: test-name", "test-name", id="test-name"),
            pytest.param(b"name: name with spaces", "name with spaces", id="name-with-spaces"),
        ],
    )
    def test_success(self, charm_path, name_line, name):
        """The metadata file is valid yaml, but there is no name."""
        # put a valid metadata
        metadata_file = charm_path / "metadata.yaml"
        with metadata_file.open("wb") as fh:
            fh.write(name_line)

        result = get_name_from_metadata()
        assert result == name

    def test_no_file(self):
        """No metadata file to get info."""
        result = get_name_from_metadata()
        assert result is None

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param(b"\b00\bff -- fake yaml", id="Not valid YAML"),
            pytest.param(b"{}", id="No name"),
        ],
    )
    def test_bad_content_garbage(self, charm_path, content):
        """The metadata file is broken."""
        # put a broken metadata
        metadata_file = charm_path / "metadata.yaml"
        with metadata_file.open("wb") as fh:
            fh.write(content)

        result = get_name_from_metadata()
        assert result is None

    def test_bad_content_no_name(self, charm_path):
        """The metadata file is valid yaml, but there is no name."""
        # put a broken metadata
        metadata_file = charm_path / "metadata.yaml"
        with metadata_file.open("wb") as fh:
            fh.write(b"{}")

        result = get_name_from_metadata()
        assert result is None
