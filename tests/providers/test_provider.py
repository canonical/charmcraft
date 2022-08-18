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
from charmcraft.config import Base


@pytest.fixture(autouse=True)
def mock_get_host_architecture():
    with patch(
        "charmcraft.providers._provider.get_host_architecture", return_value="host-arch"
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


def test_get_command_environment_minimal(monkeypatch):
    monkeypatch.setenv("IGNORE_ME", "or-im-failing")
    monkeypatch.setenv("PATH", "not-using-host-path")
    provider = providers.LXDProvider()

    env = provider.get_command_environment()

    assert env == {
        "CHARMCRAFT_MANAGED_MODE": "1",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin",
    }


def test_get_command_environment_all_opts(monkeypatch):
    monkeypatch.setenv("IGNORE_ME", "or-im-failing")
    monkeypatch.setenv("PATH", "not-using-host-path")
    monkeypatch.setenv("http_proxy", "test-http-proxy")
    monkeypatch.setenv("https_proxy", "test-https-proxy")
    monkeypatch.setenv("no_proxy", "test-no-proxy")
    provider = providers.LXDProvider()

    env = provider.get_command_environment()

    assert env == {
        "CHARMCRAFT_MANAGED_MODE": "1",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin",
        "http_proxy": "test-http-proxy",
        "https_proxy": "test-https-proxy",
        "no_proxy": "test-no-proxy",
    }


@pytest.mark.parametrize(
    "bases_index,build_on_index,project_name,target_arch,expected",
    [
        (0, 0, "mycharm", "test-arch1", "charmcraft-mycharm-{inode}-0-0-test-arch1"),
        (
            1,
            2,
            "my-other-charm",
            "test-arch2",
            "charmcraft-my-other-charm-{inode}-1-2-test-arch2",
        ),
    ],
)
def test_get_instance_name(
    bases_index, build_on_index, project_name, target_arch, expected, mock_path
):
    provider = providers.LXDProvider()

    assert provider.get_instance_name(
        bases_index=bases_index,
        build_on_index=build_on_index,
        project_name=project_name,
        project_path=mock_path,
        target_arch=target_arch,
    ) == expected.format(inode="445566")


@pytest.mark.parametrize(
    "name,channel,architectures,expected_valid,expected_reason",
    [
        ("ubuntu", "18.04", ["host-arch"], True, None),
        ("ubuntu", "20.04", ["host-arch"], True, None),
        ("ubuntu", "22.04", ["host-arch"], True, None),
        ("ubuntu", "20.04", ["extra-arch", "host-arch"], True, None),
        (
            "not-ubuntu",
            "20.04",
            ["host-arch"],
            False,
            "name 'not-ubuntu' is not yet supported (must be 'ubuntu')",
        ),
        (
            "ubuntu",
            "10.04",
            ["host-arch"],
            False,
            "channel '10.04' is not yet supported (must be '18.04', '20.04' or '22.04')",
        ),
        (
            "ubuntu",
            "20.04",
            ["other-arch"],
            False,
            "host architecture 'host-arch' not in base architectures ['other-arch']",
        ),
    ],
)
def test_is_base_available(
    mock_get_host_architecture, name, channel, architectures, expected_valid, expected_reason
):
    base = Base(name=name, channel=channel, architectures=architectures)
    provider = providers.LXDProvider()

    valid, reason = provider.is_base_available(base)

    assert (valid, reason) == (expected_valid, expected_reason)


def test_clean_project_environments_provider_not_installed(
    emitter, mock_lxc, mock_lxd_is_installed, mock_path
):
    """Assert instance is not deleted if the provider is not installed."""
    mock_lxd_is_installed.return_value = False
    provider = providers.LXDProvider(
        lxc=mock_lxc, lxd_project="test-project", lxd_remote="test-remote"
    )

    provider.clean_project_environments(
        charm_name="my-charm",
        project_path=mock_path,
        bases_index=0,
        build_on_index=0,
    )

    assert mock_lxd_is_installed.mock_calls == [call()]
    assert mock_lxc.mock_calls == []
    emitter.assert_debug("Not cleaning environment because the provider is not installed.")


def test_clean_project_environments_exists(emitter, mock_path, mock_lxd_exists, mock_lxd_delete):
    """Assert instance is deleted if it exists."""
    provider = providers.LXDProvider()

    provider.clean_project_environments(
        charm_name="my-charm-project",
        project_path=mock_path,
        bases_index=0,
        build_on_index=0,
    )

    assert mock_lxd_delete.mock_calls == [call()]
    emitter.assert_debug(
        "Cleaning environment 'charmcraft-my-charm-project-.*-0-0-host-arch'",
        regex=True,
    )


def test_clean_project_environments_does_not_exist(mock_path, mock_lxd_exists, mock_lxd_delete):
    """Assert instance is not deleted if it does not exist."""
    mock_lxd_exists.return_value = False
    provider = providers.LXDProvider()

    provider.clean_project_environments(
        charm_name="my-charm-project",
        project_path=mock_path,
        bases_index=0,
        build_on_index=0,
    )

    assert mock_lxd_delete.mock_calls == []


def test_clean_project_environments_exists_failure(mock_lxd_delete, mock_lxd_exists, mock_path):
    """Assert error on `exists` call is caught."""
    error = LXDError("fail")
    mock_lxd_exists.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        provider.clean_project_environments(
            charm_name="testcharm",
            project_path=mock_path,
            bases_index=0,
            build_on_index=0,
        )

    assert exc_info.value.__cause__ is error


def test_clean_project_environments_delete_failure(mock_lxd_delete, mock_lxd_exists, mock_path):
    """Assert error on `delete` call is caught."""
    error = LXDError("fail")
    mock_lxd_delete.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        provider.clean_project_environments(
            charm_name="testcharm",
            project_path=mock_path,
            bases_index=0,
            build_on_index=0,
        )

    assert exc_info.value.__cause__ is error
