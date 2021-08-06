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

import subprocess
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


@pytest.mark.parametrize("alias", [bases.BuilddBaseAlias.BIONIC, bases.BuilddBaseAlias.FOCAL])
def test_base_configuration_setup(mock_instance, mock_inject, monkeypatch, alias):

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    config.setup(executor=mock_instance)

    assert mock_instance.mock_calls == [
        call.execute_run(
            [
                "apt-get",
                "install",
                "-y",
                "sudo",
            ],
            check=True,
            capture_output=True,
        ),
    ]

    assert mock_inject.mock_calls == [
        call(executor=mock_instance, snap_name="charmcraft", classic=True)
    ]

    assert config.compatibility_tag == "charmcraft-buildd-base-v0.0"


def test_base_configuration_setup_apt_error(mock_instance):
    alias = bases.BuilddBaseAlias.FOCAL
    apt_cmd = ["apt-get", "install", "-y", "sudo"]
    mock_instance.execute_run.side_effect = subprocess.CalledProcessError(
        -1,
        apt_cmd,
        "some output",
        "some error",
    )

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)

    with pytest.raises(
        bases.BaseConfigurationError,
        match=r"Failed to install the required dependencies.",
    ) as exc_info:
        config.setup(executor=mock_instance)

    assert exc_info.value.__cause__ is not None


def test_base_configuration_setup_snap_injection_error(mock_instance, mock_inject):
    alias = bases.BuilddBaseAlias.FOCAL
    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    mock_inject.side_effect = snap_installer.SnapInstallationError(brief="foo error")

    with pytest.raises(
        bases.BaseConfigurationError,
        match=r"Failed to inject host Charmcraft snap into target environment.",
    ) as exc_info:
        config.setup(executor=mock_instance)

    assert exc_info.value.__cause__ is not None
