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
from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

from charmcraft import providers


@pytest.fixture(autouse=True)
def bypass_buildd_base_setup(monkeypatch):
    """Patch out inherited setup steps."""
    monkeypatch.setattr(bases.BuilddBase, "setup", lambda *args, **kwargs: None)


@pytest.fixture
def mock_executor():
    yield mock.Mock(spec=Executor)


@pytest.fixture
def mock_inject():
    with mock.patch(
        "craft_providers.actions.snap_installer.inject_from_host"
    ) as mock_inject:
        yield mock_inject


@pytest.mark.parametrize(
    "alias", [bases.BuilddBaseAlias.BIONIC, bases.BuilddBaseAlias.FOCAL]
)
def test_base_configuration_setup(mock_executor, mock_inject, monkeypatch, alias):

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    config.setup(executor=mock_executor)

    assert mock_executor.mock_calls == [
        call.execute_run(
            ["apt-get", "install", "-y", "python3-pip", "python3-setuptools"],
            check=True,
            capture_output=True,
        ),
    ]

    assert mock_inject.mock_calls == [
        call(executor=mock_executor, snap_name="charmcraft", classic=True)
    ]


def test_base_configuration_setup_apt_error(mock_executor):
    alias = bases.BuilddBaseAlias.FOCAL
    apt_cmd = ["apt-get", "install", "-y", "python3-pip", "python3-setuptools"]
    mock_executor.execute_run.side_effect = subprocess.CalledProcessError(
        -1,
        apt_cmd,
        "some output",
        "some error",
    )

    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)

    with pytest.raises(
        bases.BaseConfigurationError,
        match=r"Failed to install python3-pip and python3-setuptools.",
    ) as exc_info:
        config.setup(executor=mock_executor)

    assert exc_info.value.__cause__ is not None


def test_base_configuration_setup_snap_injection_error(mock_executor, mock_inject):
    alias = bases.BuilddBaseAlias.FOCAL
    config = providers.CharmcraftBuilddBaseConfiguration(alias=alias)
    mock_inject.side_effect = snap_installer.SnapInstallationError(brief="foo error")

    with pytest.raises(
        bases.BaseConfigurationError,
        match=r"Failed to inject host Charmcraft snap into target environment.",
    ) as exc_info:
        config.setup(executor=mock_executor)

    assert exc_info.value.__cause__ is not None
