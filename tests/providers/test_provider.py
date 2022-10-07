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

from unittest.mock import call, patch

from craft_cli import CraftError
from craft_providers.lxd import LXDError
import pytest

from charmcraft import providers


@pytest.fixture(autouse=True)
def mock_get_host_architecture():
    with patch(
        "charmcraft.providers.providers.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture()
def mock_lxc(monkeypatch):
    with patch("craft_providers.lxd.LXC", autospec=True) as mock_lxc:
        yield mock_lxc.return_value


@pytest.fixture()
def mock_lxd_delete():
    with patch("craft_providers.lxd.LXDInstance.delete") as mock_delete:
        yield mock_delete


@pytest.fixture(autouse=True)
def mock_lxd_is_installed():
    with patch("craft_providers.lxd.is_installed", return_value=True) as mock_is_installed:
        yield mock_is_installed


@pytest.fixture()
def mock_lxd_exists():
    with patch("craft_providers.lxd.LXDInstance.exists", return_value=True) as mock_exists:
        yield mock_exists


def test_clean_project_environments_provider_not_installed(
    emitter, mock_lxc, mock_lxd_is_installed, mock_path
):
    """Assert instance is not deleted if the provider is not installed."""
    mock_lxd_is_installed.return_value = False
    provider = providers.LXDProvider(
        lxc=mock_lxc, lxd_project="test-project", lxd_remote="test-remote"
    )

    provider.clean_project_environments(instance_name="test-instance-name")

    assert mock_lxd_is_installed.mock_calls == [call()]
    assert mock_lxc.mock_calls == []
    emitter.assert_debug("Not cleaning environment because the provider is not installed.")


def test_clean_project_environments_exists(emitter, mock_path, mock_lxd_exists, mock_lxd_delete):
    """Assert instance is deleted if it exists."""
    provider = providers.LXDProvider()

    provider.clean_project_environments(instance_name="test-instance-name")

    assert mock_lxd_delete.mock_calls == [call()]


def test_clean_project_environments_does_not_exist(mock_path, mock_lxd_exists, mock_lxd_delete):
    """Assert instance is not deleted if it does not exist."""
    mock_lxd_exists.return_value = False
    provider = providers.LXDProvider()

    provider.clean_project_environments(instance_name="test-instance-name")

    assert mock_lxd_delete.mock_calls == []


def test_clean_project_environments_exists_failure(mock_lxd_delete, mock_lxd_exists, mock_path):
    """Assert error on `exists` call is caught."""
    error = LXDError("fail")
    mock_lxd_exists.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        provider.clean_project_environments(instance_name="test-instance-name")

    assert exc_info.value.__cause__ is error


def test_clean_project_environments_delete_failure(mock_lxd_delete, mock_lxd_exists, mock_path):
    """Assert error on `delete` call is caught."""
    error = LXDError("fail")
    mock_lxd_delete.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        provider.clean_project_environments(instance_name="test-instance-name")

    assert exc_info.value.__cause__ is error
