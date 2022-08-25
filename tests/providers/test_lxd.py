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

import pathlib
import re
from unittest import mock
from unittest.mock import call

import pytest
from craft_cli import CraftError
from craft_providers import bases
from craft_providers.lxd import LXDError, LXDInstallationError

from charmcraft import providers
from charmcraft.config import Base


@pytest.fixture(autouse=True)
def mock_base_provider_get_host_architecture():
    with mock.patch(
        "charmcraft.providers._provider.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture()
def mock_buildd_base_configuration():
    with mock.patch(
        "charmcraft.providers._lxd.CharmcraftBuilddBaseConfiguration", autospec=True
    ) as mock_base_config:
        yield mock_base_config


@pytest.fixture()
def mock_configure_buildd_image_remote():
    with mock.patch(
        "craft_providers.lxd.configure_buildd_image_remote",
        return_value="buildd-remote",
    ) as mock_remote:
        yield mock_remote


@pytest.fixture
def mock_confirm_with_user():
    with mock.patch(
        "charmcraft.providers._lxd.confirm_with_user",
        return_value=False,
    ) as mock_confirm:
        yield mock_confirm


@pytest.fixture
def mock_lxc(monkeypatch):
    with mock.patch("craft_providers.lxd.LXC", autospec=True) as mock_lxc:
        yield mock_lxc.return_value


@pytest.fixture(autouse=True)
def mock_get_host_architecture():
    with mock.patch(
        "charmcraft.providers._lxd.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture(autouse=True)
def mock_lxd_ensure_lxd_is_ready():
    with mock.patch("craft_providers.lxd.ensure_lxd_is_ready", return_value=None) as mock_is_ready:
        yield mock_is_ready


@pytest.fixture()
def mock_lxd_install():
    with mock.patch("craft_providers.lxd.install") as mock_install:
        yield mock_install


@pytest.fixture(autouse=True)
def mock_lxd_is_installed():
    with mock.patch("craft_providers.lxd.is_installed", return_value=True) as mock_is_installed:
        yield mock_is_installed


@pytest.fixture
def mock_lxd_launch():
    with mock.patch("craft_providers.lxd.launch", autospec=True) as mock_lxd_launch:
        yield mock_lxd_launch


def test_ensure_provider_is_available_ok_when_installed(mock_lxd_is_installed):
    mock_lxd_is_installed.return_value = True
    provider = providers.LXDProvider()

    provider.ensure_provider_is_available()


def test_ensure_provider_is_available_errors_when_user_declines(
    mock_confirm_with_user, mock_lxd_is_installed
):
    mock_confirm_with_user.return_value = False
    mock_lxd_is_installed.return_value = False
    provider = providers.LXDProvider()

    with pytest.raises(
        CraftError,
        match=re.escape(
            "LXD is required, but not installed. Visit https://snapcraft.io/lxd for "
            "instructions on how to install the LXD snap for your distribution"
        ),
    ):
        provider.ensure_provider_is_available()

    assert mock_confirm_with_user.mock_calls == [
        mock.call(
            "LXD is required, but not installed. "
            "Do you wish to install LXD and configure it with the defaults?",
            default=False,
        )
    ]


def test_ensure_provider_is_available_errors_when_lxd_install_fails(
    mock_confirm_with_user, mock_lxd_is_installed, mock_lxd_install
):
    error = LXDInstallationError("foo")
    mock_confirm_with_user.return_value = True
    mock_lxd_is_installed.return_value = False
    mock_lxd_install.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(
        CraftError,
        match=re.escape(
            "Failed to install LXD. Visit https://snapcraft.io/lxd for "
            "instructions on how to install the LXD snap for your distribution"
        ),
    ) as exc_info:
        provider.ensure_provider_is_available()

    assert mock_confirm_with_user.mock_calls == [
        mock.call(
            "LXD is required, but not installed. "
            "Do you wish to install LXD and configure it with the defaults?",
            default=False,
        )
    ]
    assert exc_info.value.__cause__ is error


def test_ensure_provider_is_available_errors_when_lxd_not_ready(
    mock_confirm_with_user, mock_lxd_is_installed, mock_lxd_install, mock_lxd_ensure_lxd_is_ready
):
    error = LXDError(brief="some error", details="some details", resolution="some resolution")
    mock_confirm_with_user.return_value = True
    mock_lxd_is_installed.return_value = True
    mock_lxd_ensure_lxd_is_ready.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(
        CraftError,
        match=re.escape("some error\nsome details\nsome resolution"),
    ) as exc_info:
        provider.ensure_provider_is_available()

    assert exc_info.value.__cause__ is error


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


@pytest.mark.parametrize("is_installed", [True, False])
def test_is_provider_available(is_installed, mock_lxd_is_installed):
    mock_lxd_is_installed.return_value = is_installed
    provider = providers.LXDProvider()

    assert provider.is_provider_available() == is_installed


@pytest.mark.parametrize(
    "channel,alias",
    [("18.04", bases.BuilddBaseAlias.BIONIC), ("20.04", bases.BuilddBaseAlias.FOCAL)],
)
def test_launched_environment(
    channel,
    alias,
    mock_buildd_base_configuration,
    mock_configure_buildd_image_remote,
    mock_lxd_launch,
    monkeypatch,
    tmp_path,
):
    expected_environment = {
        "CHARMCRAFT_MANAGED_MODE": "1",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin",
    }

    base = Base(name="ubuntu", channel=channel, architectures=["host-arch"])
    provider = providers.LXDProvider()
    charm_name = f"charmcraft-test-charm-{tmp_path.stat().st_ino}-1-2-host-arch"

    with provider.launched_environment(
        charm_name="test-charm",
        project_path=tmp_path,
        base=base,
        bases_index=1,
        build_on_index=2,
    ) as instance:
        assert instance is not None
        assert mock_configure_buildd_image_remote.mock_calls == [mock.call()]
        assert mock_lxd_launch.mock_calls == [
            mock.call(
                name=charm_name,
                base_configuration=mock_buildd_base_configuration.return_value,
                image_name=channel,
                image_remote="buildd-remote",
                auto_clean=True,
                auto_create_project=True,
                map_user_uid=True,
                use_snapshots=True,
                project="charmcraft",
                remote="local",
                uid=tmp_path.stat().st_uid,
            ),
            mock.call().mount(host_source=tmp_path, target=pathlib.Path("/root/project")),
        ]
        assert mock_buildd_base_configuration.mock_calls == [
            call(
                alias=alias,
                environment=expected_environment,
                hostname=charm_name,
            )
        ]

        mock_lxd_launch.reset_mock()

    assert mock_lxd_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_launch_base_configuration_error(
    mock_buildd_base_configuration, mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = bases.BaseConfigurationError(brief="fail")
    mock_lxd_launch.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_launch_lxd_error(
    mock_buildd_base_configuration, mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_unmounts_and_stops_after_error(
    mock_buildd_base_configuration, mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.LXDProvider()

    with pytest.raises(RuntimeError):
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            mock_lxd_launch.reset_mock()
            raise RuntimeError("this is a test")

    assert mock_lxd_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_unmount_all_error(
    mock_buildd_base_configuration, mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.return_value.unmount_all.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_stop_error(
    mock_buildd_base_configuration, mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.return_value.stop.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.LXDProvider()

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error
