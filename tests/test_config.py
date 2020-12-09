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

import attr
import pytest

from charmcraft.cmdbase import CommandError
from charmcraft.config import Config, _CharmhubConfig, _check_type, _check_url


# -- tests for the config bootstrapping

def test_fromfile_current_directory(tmp_path, monkeypatch):
    """Init the config using charmcraft.yaml in current directory."""
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("""
        charmhub:
            api_url: http://foobar
    """)
    config = Config.from_file(None)
    assert config.charmhub.api_url == 'http://foobar'


def test_fromfile_specific_directory_ok(tmp_path):
    """Init the config using charmcraft.yaml in a specific directory."""
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("""
        charmhub:
            api_url: http://foobar
    """)
    config = Config.from_file(tmp_path)
    assert config.charmhub.api_url == 'http://foobar'


def test_fromfile_optional_charmcraft_missing(tmp_path):
    """Specify a directory where the file is missing."""
    config = Config.from_file(tmp_path)
    default = _CharmhubConfig.__attrs_attrs__[0].default
    assert config.charmhub.api_url == default


def test_fromfile_must_be_dict(tmp_path):
    """The charmcraft.yaml content must be a dict."""
    test_file = tmp_path / "charmcraft.yaml"
    test_file.write_text("33")
    with pytest.raises(CommandError) as cm:
        Config.from_file(tmp_path)
    assert str(cm.value) == "Invalid charmcraft.yaml structure: must be a dictionary."


def test_config_type_validation():
    """The type of each value is verified."""
    with pytest.raises(CommandError) as cm:
        Config(charmhub='bad stuff')
    assert str(cm.value) == (
        "Bad charmcraft.yaml content: the 'charmhub' field must be a dict: got 'str'.")


def test_config_frozen():
    """Cannot change values from the config."""
    config = Config()
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        config.charmhub = 'broken'


# -- tests for different validators


@attr.s
class FakeConfig:
    """Helper with a simple field to be used to test validators."""
    section = None
    test_string = attr.ib(type=str, default='foo', validator=[_check_type])
    test_url = attr.ib(type=str, default='http://localhost:0', validator=[_check_url])


def test_type_ok():
    """Type validation succeeds."""
    FakeConfig(test_string='some ok string')


def test_type_wrong_main_key():
    """Type doesn't validate for a key in the main config."""
    with pytest.raises(CommandError) as cm:
        FakeConfig(test_string=33)
    assert str(cm.value) == "The config value test_string must be a str: got 33"


def test_type_wrong_deep_key(monkeypatch):
    """Type doesn't validate for a key under other section."""
    monkeypatch.setattr(FakeConfig, 'section', 'testsection')
    with pytest.raises(CommandError) as cm:
        FakeConfig(test_string=33)
    assert str(cm.value) == "The config value testsection.test_string must be a str: got 33"


def test_url_ok():
    """URL format is ok."""
    FakeConfig(test_url='https://some.server.com')


def test_url_no_scheme():
    """URL format is wrong, missing scheme."""
    with pytest.raises(CommandError) as cm:
        FakeConfig(test_url='some.server.com')
    assert str(cm.value) == (
        "The config value test_url must be a full URL (e.g. 'https://some.server.com'): "
        "got 'some.server.com'")


def test_url_no_netloc():
    """URL format is wrong, missing network location."""
    with pytest.raises(CommandError) as cm:
        FakeConfig(test_url='https://')
    assert str(cm.value) == (
        "The config value test_url must be a full URL (e.g. 'https://some.server.com'): "
        "got 'https://'")


# -- tests for Charmhub config

def test_charmhub_frozen():
    """Cannot change values from the charmhub config."""
    config = _CharmhubConfig()
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        config.api_url = 'broken'


def test_charmhub_from_bad_structure():
    """Instantiate charmhub using a bad structure."""
    with pytest.raises(CommandError) as cm:
        _CharmhubConfig.from_dict([1, 2])
    assert str(cm.value) == (
        "Bad charmcraft.yaml content: the 'charmhub' field must be a dict: got 'list'.")


def test_charmhub_from_dict_with_full_values():
    """Instantiate charmhub config with all values from config."""
    src = dict(api_url='http://api', storage_url='http://storage')
    config = _CharmhubConfig.from_dict(src)
    assert config.api_url == 'http://api'
    assert config.storage_url == 'http://storage'


def test_charmhub_from_dict_with_some_values():
    """Instantiate charmhub config with some values from config."""
    src = dict(api_url='http://api')
    config = _CharmhubConfig.from_dict(src)
    assert config.api_url == 'http://api'
    assert config.storage_url == 'https://storage.staging.snapcraftcontent.com'


def test_charmhub_from_dict_with_no_values():
    """Instantiate charmhub config from empty config."""
    config = _CharmhubConfig.from_dict({})
    assert config.api_url == 'https://api.staging.charmhub.io'
    assert config.storage_url == 'https://storage.staging.snapcraftcontent.com'
