# Copyright 2021 Canonical Ltd.
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
from unittest import mock

import pytest
import snaphelpers

from charmcraft.snap import (
    CharmcraftSnapConfiguration,
    get_snap_configuration,
    validate_snap_configuration,
)


@pytest.fixture
def mock_snap_config():
    with mock.patch("charmcraft.snap.snaphelpers.SnapConfig", autospec=True) as mock_snap_config:
        yield mock_snap_config


def test_get_snap_configuration_empty(mock_snap_config):
    def fake_get(key: str):
        raise snaphelpers._conf.UnknownConfigKey(key=key)

    mock_snap_config.return_value.get.side_effect = fake_get

    snap_config = get_snap_configuration()

    assert snap_config == CharmcraftSnapConfiguration()


@pytest.mark.parametrize("provider", ["lxd", "multipass"])
def test_get_snap_configuration_valid_providers(mock_snap_config, provider):
    def fake_get(key: str):
        if key == "provider":
            return provider
        raise snaphelpers._conf.UnknownConfigKey(key=key)

    mock_snap_config.return_value.get.side_effect = fake_get

    snap_config = get_snap_configuration()

    assert snap_config == CharmcraftSnapConfiguration(provider=provider)


@pytest.mark.parametrize("provider", ["", "invalid"])
def test_get_snap_configuration_invalid_providers(mock_snap_config, provider):
    def fake_get(key: str):
        if key == "provider":
            return provider
        raise snaphelpers._conf.UnknownConfigKey(key=key)

    mock_snap_config.return_value.get.side_effect = fake_get

    snap_config = get_snap_configuration()

    assert snap_config == CharmcraftSnapConfiguration(provider=provider)
    assert snap_config.provider == provider

    with pytest.raises(ValueError, match=re.escape(f"provider {provider!r} is not supported")):
        validate_snap_configuration(snap_config)
