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
from craft_providers.multipass import MultipassError, MultipassInstallationError

from charmcraft import providers
from charmcraft.config import Base
from charmcraft.providers.providers import get_base_configuration


@pytest.fixture(autouse=True)
def mock_base_provider_get_host_architecture():
    with mock.patch(
        "charmcraft.providers._provider.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture
def mock_confirm_with_user():
    with mock.patch(
        "charmcraft.providers._multipass.confirm_with_user",
        return_value=False,
    ) as mock_confirm:
        yield mock_confirm


@pytest.fixture
def mock_multipass(monkeypatch):
    with mock.patch("craft_providers.multipass.Multipass", autospec=True) as mock_client:
        yield mock_client.return_value


@pytest.fixture(autouse=True)
def mock_multipass_ensure_multipass_is_ready():
    with mock.patch(
        "craft_providers.multipass.ensure_multipass_is_ready", return_value=None
    ) as mock_is_ready:
        yield mock_is_ready


@pytest.fixture()
def mock_multipass_install():
    with mock.patch("craft_providers.multipass.install") as mock_install:
        yield mock_install


@pytest.fixture(autouse=True)
def mock_multipass_is_installed():
    with mock.patch(
        "craft_providers.multipass.is_installed", return_value=True
    ) as mock_is_installed:
        yield mock_is_installed


@pytest.fixture
def mock_multipass_launch():
    with mock.patch("craft_providers.multipass.launch", autospec=True) as mock_multipass_launch:
        yield mock_multipass_launch


def test_ensure_provider_is_available_ok_when_installed(mock_multipass_is_installed):
    mock_multipass_is_installed.return_value = True
    provider = providers.MultipassProvider()

    provider.ensure_provider_is_available()


def test_ensure_provider_is_available_errors_when_user_declines(
    mock_confirm_with_user, mock_multipass_is_installed
):
    mock_confirm_with_user.return_value = False
    mock_multipass_is_installed.return_value = False
    provider = providers.MultipassProvider()

    match = re.escape(
        "Multipass is required, but not installed. Visit https://multipass.run/ for "
        "instructions on installing Multipass for your operating system."
    )
    with pytest.raises(CraftError, match=match):
        provider.ensure_provider_is_available()

    assert mock_confirm_with_user.mock_calls == [
        mock.call(
            "Multipass is required, but not installed. "
            "Do you wish to install Multipass and configure it with the defaults?",
            default=False,
        )
    ]


def test_ensure_provider_is_available_errors_when_multipass_install_fails(
    mock_confirm_with_user, mock_multipass_is_installed, mock_multipass_install
):
    error = MultipassInstallationError("foo")
    mock_confirm_with_user.return_value = True
    mock_multipass_is_installed.return_value = False
    mock_multipass_install.side_effect = error
    provider = providers.MultipassProvider()

    match = re.escape(
        "Failed to install Multipass. Visit https://multipass.run/ for "
        "instructions on installing Multipass for your operating system."
    )
    with pytest.raises(CraftError, match=match) as exc_info:
        provider.ensure_provider_is_available()

    assert mock_confirm_with_user.mock_calls == [
        mock.call(
            "Multipass is required, but not installed. "
            "Do you wish to install Multipass and configure it with the defaults?",
            default=False,
        )
    ]
    assert exc_info.value.__cause__ is error


def test_ensure_provider_is_available_errors_when_multipass_not_ready(
    mock_confirm_with_user,
    mock_multipass_is_installed,
    mock_multipass_install,
    mock_multipass_ensure_multipass_is_ready,
):
    error = MultipassError(
        brief="some error", details="some details", resolution="some resolution"
    )
    mock_confirm_with_user.return_value = True
    mock_multipass_is_installed.return_value = True
    mock_multipass_ensure_multipass_is_ready.side_effect = error
    provider = providers.MultipassProvider()

    with pytest.raises(
        CraftError,
        match=re.escape("some error\nsome details\nsome resolution"),
    ) as exc_info:
        provider.ensure_provider_is_available()

    assert exc_info.value.__cause__ is error


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
def test_is_base_available(name, channel, architectures, expected_valid, expected_reason):
    base = Base(name=name, channel=channel, architectures=architectures)
    provider = providers.MultipassProvider()

    valid, reason = provider.is_base_available(base)

    assert (valid, reason) == (expected_valid, expected_reason)


@pytest.mark.parametrize("is_installed", [True, False])
def test_is_provider_installed(is_installed, mock_multipass_is_installed):
    mock_multipass_is_installed.return_value = is_installed
    provider = providers.MultipassProvider()

    assert provider.is_provider_installed() == is_installed


@pytest.mark.parametrize(
    "channel,alias",
    [("18.04", bases.BuilddBaseAlias.BIONIC), ("20.04", bases.BuilddBaseAlias.FOCAL)],
)
def test_launched_environment(channel, alias, mock_multipass_launch, mock_path):
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(alias=alias, instance_name=instance_name)

    with provider.launched_environment(
        charm_name="test-charm",
        project_path=mock_path,
        base_configuration=base_configuration,
        build_base=channel,
        instance_name=instance_name,
    ) as instance:
        assert instance is not None
        assert mock_multipass_launch.mock_calls == [
            mock.call(
                name=instance_name,
                base_configuration=base_configuration,
                image_name=f"snapcraft:{channel}",
                cpus=2,
                disk_gb=64,
                mem_gb=2,
                auto_clean=True,
            ),
        ]

        mock_multipass_launch.reset_mock()

    assert mock_multipass_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_unmounts_and_stops_after_error(mock_multipass_launch, tmp_path):
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.BIONIC, instance_name=instance_name
    )

    with pytest.raises(RuntimeError):
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base_configuration=base_configuration,
            build_base="20.04",
            instance_name=instance_name,
        ):
            mock_multipass_launch.reset_mock()
            raise RuntimeError("this is a test")

    assert mock_multipass_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_launch_base_configuration_error(mock_multipass_launch, tmp_path):
    error = bases.BaseConfigurationError(brief="fail")
    mock_multipass_launch.side_effect = error
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.BIONIC, instance_name=instance_name
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


def test_launched_environment_launch_multipass_error(mock_multipass_launch, tmp_path):
    error = MultipassError(brief="fail")
    mock_multipass_launch.side_effect = error
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.BIONIC, instance_name=instance_name
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


def test_launched_environment_unmount_all_error(mock_multipass_launch, tmp_path):
    error = MultipassError(brief="fail")
    mock_multipass_launch.return_value.unmount_all.side_effect = error
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.BIONIC, instance_name=instance_name
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


def test_launched_environment_stop_error(mock_multipass_launch, tmp_path):
    error = MultipassError(brief="fail")
    mock_multipass_launch.return_value.stop.side_effect = error
    provider = providers.MultipassProvider()
    instance_name = "test-instance-name"
    base_configuration = get_base_configuration(
        alias=bases.BuilddBaseAlias.BIONIC, instance_name=instance_name
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
