# Copyright 2020 Canonical Ltd.
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

import pytest

from charmcraft.cmdbase import CommandError
from charmcraft.config import _Config


def test_default_data():
    """By default the config is empty."""
    config = _Config()
    assert config == {}


def test_init_current_directory(tmp_path, monkeypatch):
    """Init the config using charmcraft.yaml in current directory."""
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("foo: 33")
    config = _Config()
    config.init(None)
    assert config == {'foo': 33}


def test_init_specific_directory_ok(tmp_path):
    """Init the config using charmcraft.yaml in a specific directory."""
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("foo: 33")
    config = _Config()
    config.init(tmp_path)
    assert config == {'foo': 33}


def test_init_optional_charmcraft_missing(tmp_path):
    """Specify a directory which is not there."""
    config = _Config()
    config.init(tmp_path)
    assert config == {}


def test_validate_must_be_dict(tmp_path):
    """The charmcraft.yaml content must be a dict."""
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("33")
    config = _Config()
    with pytest.raises(CommandError) as cm:
        config.init(tmp_path)
    assert str(cm.value) == "Invalid charmcraft.yaml structure: must be a dictionary."
