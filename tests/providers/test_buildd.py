# Copyright 2021-2022 Canonical Ltd.
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
import sys
from unittest import mock
from unittest.mock import call

import pytest
from craft_providers import bases
from craft_providers.actions import snap_installer

from charmcraft import providers


@pytest.fixture
def mock_inject():
    with mock.patch("craft_providers.actions.snap_installer.inject_from_host") as mock_inject:
        yield mock_inject


@pytest.fixture
def mock_install_from_store():
    with mock.patch("craft_providers.actions.snap_installer.install_from_store") as mock_install:
        yield mock_install


@pytest.mark.parametrize("alias", [bases.BuilddBaseAlias.BIONIC, bases.BuilddBaseAlias.FOCAL])
@pytest.mark.parametrize("method_name", ["setup", "warmup"])
def test_base_configuration_setup_inject_from_host(
    mock_instance, mock_inject, mock_install_from_store, monkeypatch, alias, method_name
):
    monkeypatch.setattr(sys, "platform", "linux")

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    preparation_method = getattr(config, method_name)
    preparation_method(executor=mock_instance)

    assert mock_inject.mock_calls == [
        call(executor=mock_instance, snap_name="charmcraft", classic=True)
    ]
    assert mock_install_from_store.mock_calls == []

    assert config.compatibility_tag == "charmcraft-buildd-base-v0.0"


@pytest.mark.parametrize("alias", [bases.BuilddBaseAlias.BIONIC, bases.BuilddBaseAlias.FOCAL])
@pytest.mark.parametrize("method_name", ["setup", "warmup"])
def test_base_configuration_setup_from_store(
    mock_instance, mock_inject, mock_install_from_store, monkeypatch, alias, method_name
):
    channel = "test-track/test-channel"
    monkeypatch.setenv("CHARMCRAFT_INSTALL_SNAP_CHANNEL", channel)

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    preparation_method = getattr(config, method_name)
    preparation_method(executor=mock_instance)

    assert mock_inject.mock_calls == []
    assert mock_install_from_store.mock_calls == [
        call(executor=mock_instance, snap_name="charmcraft", channel=channel, classic=True)
    ]

    assert config.compatibility_tag == "charmcraft-buildd-base-v0.0"


@pytest.mark.parametrize("alias", [bases.BuilddBaseAlias.BIONIC, bases.BuilddBaseAlias.FOCAL])
@pytest.mark.parametrize("method_name", ["setup", "warmup"])
def test_base_configuration_setup_from_store_default_for_windows(
    mock_instance, mock_inject, mock_install_from_store, monkeypatch, alias, method_name
):
    monkeypatch.setattr(sys, "platform", "win32")

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    preparation_method = getattr(config, method_name)
    preparation_method(executor=mock_instance)

    assert mock_inject.mock_calls == []
    assert mock_install_from_store.mock_calls == [
        call(executor=mock_instance, snap_name="charmcraft", channel="stable", classic=True)
    ]

    assert config.compatibility_tag == "charmcraft-buildd-base-v0.0"


@pytest.mark.parametrize("method_name", ["setup", "warmup"])
def test_base_configuration_setup_snap_injection_error(
    mock_instance, mock_inject, monkeypatch, method_name
):
    monkeypatch.setattr(sys, "platform", "linux")

    alias = bases.BuilddBaseAlias.FOCAL
    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    mock_inject.side_effect = snap_installer.SnapInstallationError(brief="foo error")

    preparation_method = getattr(config, method_name)
    with pytest.raises(
        bases.BaseConfigurationError,
        match=r"Failed to inject host Charmcraft snap into target environment.",
    ) as exc_info:
        preparation_method(executor=mock_instance)

    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize("method_name", ["setup", "warmup"])
def test_base_configuration_setup_snap_install_from_store_error(
    mock_instance, mock_install_from_store, monkeypatch, method_name
):
    channel = "test-track/test-channel"
    monkeypatch.setenv("CHARMCRAFT_INSTALL_SNAP_CHANNEL", channel)
    alias = bases.BuilddBaseAlias.FOCAL
    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    mock_install_from_store.side_effect = snap_installer.SnapInstallationError(brief="foo error")
    match = re.escape(
        "Failed to install Charmcraft snap from store channel "
        "'test-track/test-channel' into target environment."
    )

    preparation_method = getattr(config, method_name)
    with pytest.raises(
        bases.BaseConfigurationError,
        match=match,
    ) as exc_info:
        preparation_method(executor=mock_instance)

    assert exc_info.value.__cause__ is not None
