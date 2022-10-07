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
from unittest import mock

import pytest
from craft_cli import CraftError
from craft_providers import bases
from craft_providers.lxd import LXDError, LXDInstallationError

from charmcraft import providers
from charmcraft.providers.providers import get_base_configuration


@pytest.fixture(autouse=True)
def mock_base_provider_get_host_architecture():
    with mock.patch(
        "charmcraft.providers.providers.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture()
def mock_configure_buildd_image_remote():
    with mock.patch(
        "craft_providers.lxd.configure_buildd_image_remote",
        return_value="buildd-remote",
    ) as mock_remote:
        yield mock_remote


@pytest.fixture
def mock_lxc(monkeypatch):
    with mock.patch("craft_providers.lxd.LXC", autospec=True) as mock_lxc:
        yield mock_lxc.return_value


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


def test_ensure_provider_is_available_errors_when_lxd_install_fails(
    mock_lxd_is_installed, mock_lxd_install
):
    error = LXDInstallationError("foo")
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

    assert exc_info.value.__cause__ is error


def test_ensure_provider_is_available_errors_when_lxd_not_ready(
    mock_lxd_is_installed, mock_lxd_install, mock_lxd_ensure_lxd_is_ready
):
    error = LXDError(brief="some error", details="some details", resolution="some resolution")
    mock_lxd_is_installed.return_value = True
    mock_lxd_ensure_lxd_is_ready.side_effect = error
    provider = providers.LXDProvider()

    with pytest.raises(
        CraftError,
        match=re.escape("some error\nsome details\nsome resolution"),
    ) as exc_info:
        provider.ensure_provider_is_available()

    assert exc_info.value.__cause__ is error


@pytest.mark.parametrize("is_installed", [True, False])
def test_is_provider_installed(is_installed, mock_lxd_is_installed):
    mock_lxd_is_installed.return_value = is_installed
    provider = providers.LXDProvider()

    assert provider.is_provider_installed() == is_installed


@pytest.mark.parametrize(
    "channel,alias",
    [
        ("18.04", bases.BuilddBaseAlias.BIONIC),
        ("20.04", bases.BuilddBaseAlias.FOCAL),
    ],
)
def test_launched_environment(
    channel,
    alias,
    mock_configure_buildd_image_remote,
    mock_lxd_launch,
    monkeypatch,
    tmp_path,
):

    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(alias=alias, instance_name=instance_name)

    with provider.launched_environment(
        charm_name="test-charm",
        project_path=tmp_path,
        base_configuration=base_configuration,
        build_base=channel,
        instance_name=instance_name,
    ) as instance:
        assert instance is not None
        assert mock_configure_buildd_image_remote.mock_calls == [mock.call()]
        assert mock_lxd_launch.mock_calls == [
            mock.call(
                name=instance_name,
                base_configuration=base_configuration,
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
        ]

        mock_lxd_launch.reset_mock()

    assert mock_lxd_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_launch_base_configuration_error(
    mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = bases.BaseConfigurationError(brief="fail")
    mock_lxd_launch.side_effect = error
    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.FOCAL, instance_name=instance_name
    )

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_launch_lxd_error(
    mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.side_effect = error
    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.FOCAL, instance_name=instance_name
    )

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_unmounts_and_stops_after_error(
    mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.FOCAL, instance_name=instance_name
    )

    with pytest.raises(RuntimeError):
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            mock_lxd_launch.reset_mock()
            raise RuntimeError("this is a test")

    assert mock_lxd_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_unmount_all_error(
    mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.return_value.unmount_all.side_effect = error
    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.FOCAL, instance_name=instance_name
    )

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_stop_error(
    mock_configure_buildd_image_remote, mock_lxd_launch, tmp_path
):
    error = LXDError(brief="fail")
    mock_lxd_launch.return_value.stop.side_effect = error
    provider = providers.LXDProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.FOCAL, instance_name=instance_name
    )

    with pytest.raises(CraftError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            pass

    assert exc_info.value.__cause__ is error
