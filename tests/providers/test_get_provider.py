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

import sys
from unittest import mock

import pytest

from charmcraft.providers import LXDProvider, MultipassProvider, get_provider
from charmcraft.snap import CharmcraftSnapConfiguration


@pytest.fixture(autouse=True)
def mock_snap_config():
    with mock.patch(
        "charmcraft.providers._get_provider.get_snap_configuration", return_value=None
    ) as mock_snap:
        yield mock_snap


@pytest.fixture(autouse=True)
def mock_is_developer_mode():
    with mock.patch(
        "charmcraft.providers._get_provider.is_charmcraft_running_in_developer_mode",
        return_value=False,
    ) as mock_is_dev_mode:
        yield mock_is_dev_mode


@pytest.fixture(autouse=True)
def mock_is_snap():
    with mock.patch(
        "charmcraft.providers._get_provider.is_charmcraft_running_from_snap", return_value=False
    ) as mock_is_snap:
        yield mock_is_snap


def test_get_provider_default():
    if sys.platform == "linux":
        assert isinstance(get_provider(), LXDProvider)
    else:
        assert isinstance(get_provider(), MultipassProvider)


def test_get_provider_developer_mode_env(monkeypatch, mock_is_developer_mode):
    mock_is_developer_mode.return_value = True
    monkeypatch.setenv("CHARMCRAFT_PROVIDER", "lxd")
    assert isinstance(get_provider(), LXDProvider)

    monkeypatch.setenv("CHARMCRAFT_PROVIDER", "multipass")
    assert isinstance(get_provider(), MultipassProvider)


def test_get_provider_snap_config(mock_is_snap, mock_snap_config):
    mock_is_snap.return_value = True

    mock_snap_config.return_value = CharmcraftSnapConfiguration(provider="lxd")
    assert isinstance(get_provider(), LXDProvider)

    mock_snap_config.return_value = CharmcraftSnapConfiguration(provider="multipass")
    assert isinstance(get_provider(), MultipassProvider)
