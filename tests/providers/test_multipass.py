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

import pathlib
import re
from unittest import mock
from unittest.mock import call

import pytest
from craft_providers import bases
from craft_providers.multipass import MultipassError, MultipassInstallationError

from charmcraft import providers
from charmcraft.cmdbase import CommandError
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
        "charmcraft.providers._multipass.CharmcraftBuilddBaseConfiguration", autospec=True
    ) as mock_base_config:
        yield mock_base_config


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
def mock_get_host_architecture():
    with mock.patch(
        "charmcraft.providers._multipass.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


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


def test_clean_project_environments_without_multipass(
    mock_multipass, mock_multipass_is_installed, mock_path
):
    mock_multipass_is_installed.return_value = False
    provider = providers.MultipassProvider(multipass=mock_multipass)

    assert (
        provider.clean_project_environments(
            charm_name="my-charm",
            project_path=mock_path,
        )
        == []
    )

    assert mock_multipass_is_installed.mock_calls == [mock.call()]
    assert mock_multipass.mock_calls == []


def test_clean_project_environments(mock_multipass, mock_path):
    mock_multipass.list.return_value = [
        "do-not-delete-me-please",
        "charmcraft-testcharm-445566-b-c-d",
        "charmcraft-my-charm---",
        "charmcraft-my-charm-445566---",
        "charmcraft-my-charm-project-445566-0-0-amd99",
        "charmcraft-my-charm-project-445566-999-444-arm64",
        "charmcraft_445566_a_b_c_d",
    ]
    provider = providers.MultipassProvider(multipass=mock_multipass)

    assert provider.clean_project_environments(
        charm_name="my-charm-project",
        project_path=mock_path,
    ) == [
        "charmcraft-my-charm-project-445566-0-0-amd99",
        "charmcraft-my-charm-project-445566-999-444-arm64",
    ]
    assert mock_multipass.mock_calls == [
        mock.call.list(),
        mock.call.delete(
            instance_name="charmcraft-my-charm-project-445566-0-0-amd99",
            purge=True,
        ),
        mock.call.delete(
            instance_name="charmcraft-my-charm-project-445566-999-444-arm64",
            purge=True,
        ),
    ]

    mock_multipass.reset_mock()

    assert provider.clean_project_environments(
        charm_name="testcharm",
        project_path=mock_path,
    ) == [
        "charmcraft-testcharm-445566-b-c-d",
    ]
    assert mock_multipass.mock_calls == [
        mock.call.list(),
        mock.call.delete(
            instance_name="charmcraft-testcharm-445566-b-c-d",
            purge=True,
        ),
    ]

    mock_multipass.reset_mock()

    assert (
        provider.clean_project_environments(
            charm_name="unknown-charm",
            project_path=mock_path,
        )
        == []
    )
    assert mock_multipass.mock_calls == [
        mock.call.list(),
    ]


def test_clean_project_environments_list_failure(mock_multipass, mock_path):
    error = MultipassError(brief="fail")
    mock_multipass.list.side_effect = error
    provider = providers.MultipassProvider(multipass=mock_multipass)

    with pytest.raises(CommandError, match="fail") as exc_info:
        provider.clean_project_environments(
            charm_name="charm",
            project_path=mock_path,
        )

    assert exc_info.value.__cause__ is error


def test_clean_project_environments_delete_failure(mock_multipass, mock_path):
    error = MultipassError(brief="fail")
    mock_multipass.list.return_value = ["charmcraft-testcharm-445566-b-c-d"]
    mock_multipass.delete.side_effect = error
    provider = providers.MultipassProvider(multipass=mock_multipass)

    with pytest.raises(CommandError, match="fail") as exc_info:
        provider.clean_project_environments(
            charm_name="testcharm",
            project_path=mock_path,
        )

    assert exc_info.value.__cause__ is error


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
    with pytest.raises(CommandError, match=match):
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
    with pytest.raises(CommandError, match=match) as exc_info:
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
        CommandError,
        match=re.escape("some error\nsome details\nsome resolution"),
    ) as exc_info:
        provider.ensure_provider_is_available()

    assert exc_info.value.__cause__ is error


def test_get_command_environment_minimal(monkeypatch):
    monkeypatch.setenv("IGNORE_ME", "or-im-failing")
    monkeypatch.setenv("PATH", "not-using-host-path")
    provider = providers.MultipassProvider()

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
    provider = providers.MultipassProvider()

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
    provider = providers.MultipassProvider()

    assert (
        provider.get_instance_name(
            bases_index=bases_index,
            build_on_index=build_on_index,
            project_name=project_name,
            project_path=mock_path,
            target_arch=target_arch,
        )
        == expected.format(inode="445566")
    )


@pytest.mark.parametrize(
    "name,channel,architectures,expected_valid,expected_reason",
    [
        ("ubuntu", "18.04", ["host-arch"], True, None),
        ("ubuntu", "20.04", ["host-arch"], True, None),
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
            "channel '10.04' is not yet supported (must be '18.04' or '20.04')",
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
    provider = providers.MultipassProvider()

    valid, reason = provider.is_base_available(base)

    assert (valid, reason) == (expected_valid, expected_reason)


@pytest.mark.parametrize("is_installed", [True, False])
def test_is_provider_available(is_installed, mock_multipass_is_installed):
    mock_multipass_is_installed.return_value = is_installed
    provider = providers.MultipassProvider()

    assert provider.is_provider_available() == is_installed


@pytest.mark.parametrize(
    "channel,alias",
    [("18.04", bases.BuilddBaseAlias.BIONIC), ("20.04", bases.BuilddBaseAlias.FOCAL)],
)
def test_launched_environment(
    channel,
    alias,
    mock_buildd_base_configuration,
    mock_multipass_launch,
    monkeypatch,
    tmp_path,
    mock_path,
):
    expected_environment = {
        "CHARMCRAFT_MANAGED_MODE": "1",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin",
    }

    base = Base(name="ubuntu", channel=channel, architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with provider.launched_environment(
        charm_name="test-charm",
        project_path=mock_path,
        base=base,
        bases_index=1,
        build_on_index=2,
    ) as instance:
        assert instance is not None
        assert mock_multipass_launch.mock_calls == [
            mock.call(
                name="charmcraft-test-charm-445566-1-2-host-arch",
                base_configuration=mock_buildd_base_configuration.return_value,
                image_name=channel,
                cpus=2,
                disk_gb=64,
                mem_gb=2,
                auto_clean=True,
            ),
            mock.call().mount(host_source=mock_path, target=pathlib.Path("/root/project")),
        ]
        assert mock_buildd_base_configuration.mock_calls == [
            call(
                alias=alias,
                environment=expected_environment,
                hostname="charmcraft-test-charm-445566-1-2-host-arch",
            )
        ]

        mock_multipass_launch.reset_mock()

    assert mock_multipass_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_unmounts_and_stops_after_error(
    mock_buildd_base_configuration, mock_multipass_launch, tmp_path
):
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with pytest.raises(RuntimeError):
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            mock_multipass_launch.reset_mock()
            raise RuntimeError("this is a test")

    assert mock_multipass_launch.mock_calls == [
        mock.call().unmount_all(),
        mock.call().stop(),
    ]


def test_launched_environment_launch_base_configuration_error(
    mock_buildd_base_configuration, mock_multipass_launch, tmp_path
):
    error = bases.BaseConfigurationError(brief="fail")
    mock_multipass_launch.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with pytest.raises(CommandError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_launch_multipass_error(
    mock_buildd_base_configuration, mock_multipass_launch, tmp_path
):
    error = MultipassError(brief="fail")
    mock_multipass_launch.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with pytest.raises(CommandError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error


def test_launched_environment_unmount_all_error(
    mock_buildd_base_configuration, mock_multipass_launch, tmp_path
):
    error = MultipassError(brief="fail")
    mock_multipass_launch.return_value.unmount_all.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with pytest.raises(CommandError, match="fail") as exc_info:
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
    mock_buildd_base_configuration, mock_multipass_launch, tmp_path
):
    error = MultipassError(brief="fail")
    mock_multipass_launch.return_value.stop.side_effect = error
    base = Base(name="ubuntu", channel="20.04", architectures=["host-arch"])
    provider = providers.MultipassProvider()

    with pytest.raises(CommandError, match="fail") as exc_info:
        with provider.launched_environment(
            charm_name="test-charm",
            project_path=tmp_path,
            base=base,
            bases_index=1,
            build_on_index=2,
        ):
            pass

    assert exc_info.value.__cause__ is error
