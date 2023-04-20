# Copyright 2022 Canonical Ltd.
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

import contextlib
import pathlib
import sys
from unittest.mock import Mock, patch, call

import pytest
from craft_cli import CraftError
from craft_providers import ProviderError, bases, lxd, multipass
from craft_providers.actions.snap_installer import Snap

from charmcraft.config import Base, BasesConfiguration
from charmcraft import providers
from charmcraft.snap import CharmcraftSnapConfiguration


@pytest.fixture()
def mock_provider(mock_instance, fake_provider):
    mock_provider = Mock(wraps=fake_provider)
    with patch("charmcraft.commands.build.providers.get_provider", return_value=mock_provider):
        yield mock_provider


@pytest.fixture()
def mock_is_base_available():
    with patch(
        "charmcraft.providers.is_base_available", return_value=(True, None)
    ) as mock_is_base_available:
        yield mock_is_base_available


@pytest.fixture()
def mock_check_if_base_matches_host():
    with patch(
        "charmcraft.providers.check_if_base_matches_host", return_value=(True, None)
    ) as mock_check_if_base_matches_host:
        yield mock_check_if_base_matches_host


@pytest.fixture()
def mock_get_host_architecture():
    with patch(
        "charmcraft.providers.get_host_architecture", return_value="host-arch"
    ) as mock_arch:
        yield mock_arch


@pytest.fixture()
def mock_snap_config():
    with patch("charmcraft.providers.get_snap_configuration", return_value=None) as mock_snap:
        yield mock_snap


@pytest.fixture()
def mock_is_developer_mode():
    with patch(
        "charmcraft.providers.is_charmcraft_running_in_developer_mode",
        return_value=False,
    ) as mock_is_dev_mode:
        yield mock_is_dev_mode


@pytest.fixture()
def mock_is_snap():
    with patch(
        "charmcraft.providers.is_charmcraft_running_from_snap", return_value=False
    ) as mock_is_snap:
        yield mock_is_snap


@pytest.fixture()
def simple_base_config():
    """Yields a simple BaseConfiguration object."""
    yield [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                ],
                "run-on": [
                    Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                ],
            }
        ),
    ]


@pytest.fixture()
def complex_base_config():
    """Yields a complex list of BaseConfiguration objects."""
    yield [
        # 1 build-on and 1 run-on
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                ],
                "run-on": [
                    Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                ],
            }
        ),
        # 2 build-on and 1 run-on
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                    Base(name="x4name", channel="x4channel", architectures=["x4arch"]),
                ],
                "run-on": [
                    Base(name="x5name", channel="x5channel", architectures=["x5arch"]),
                ],
            }
        ),
        # 1 build-on and 2 run-on with multiple architectures
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
                ],
                "run-on": [
                    Base(name="x7name", channel="x7channel", architectures=["x7arch"]),
                    Base(
                        name="x8name",
                        channel="x8channel",
                        architectures=["x8arch1", "x8arch2"],
                    ),
                ],
            }
        ),
    ]


def test_create_build_plan_simple(
    emitter, mock_provider, mock_is_base_available, simple_base_config
):
    """Verify creation of a simple build plan."""
    build_plan = providers.create_build_plan(
        bases=simple_base_config,
        bases_indices=None,
        destructive_mode=False,
        managed_mode=False,
        provider=mock_provider,
    )

    assert build_plan == [
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                    ],
                    "run-on": [
                        Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                    ],
                }
            ),
            build_on=Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
            bases_index=0,
            build_on_index=0,
        ),
    ]
    emitter.assert_interactions(
        [
            call("debug", "Building for 'bases[0]' as host matches 'build-on[0]'."),
        ]
    )


def test_create_build_plan_complex(
    emitter, complex_base_config, mock_provider, mock_is_base_available
):
    """Verify creation of a complex build plan."""

    build_plan = providers.create_build_plan(
        bases=complex_base_config,
        bases_indices=None,
        destructive_mode=False,
        managed_mode=False,
        provider=mock_provider,
    )

    assert build_plan == [
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                    ],
                    "run-on": [
                        Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                    ],
                }
            ),
            build_on=Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
            bases_index=0,
            build_on_index=0,
        ),
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                        Base(name="x4name", channel="x4channel", architectures=["x4arch"]),
                    ],
                    "run-on": [
                        Base(name="x5name", channel="x5channel", architectures=["x5arch"]),
                    ],
                }
            ),
            build_on=Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
            bases_index=1,
            build_on_index=0,
        ),
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
                    ],
                    "run-on": [
                        Base(name="x7name", channel="x7channel", architectures=["x7arch"]),
                        Base(
                            name="x8name",
                            channel="x8channel",
                            architectures=["x8arch1", "x8arch2"],
                        ),
                    ],
                }
            ),
            build_on=Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
            bases_index=2,
            build_on_index=0,
        ),
    ]
    emitter.assert_interactions(
        [
            call("debug", "Building for 'bases[0]' as host matches 'build-on[0]'."),
            call("debug", "Building for 'bases[1]' as host matches 'build-on[0]'."),
            call("debug", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


@pytest.mark.parametrize("destructive_mode, managed_mode", [(True, False), (False, True)])
def test_create_build_plan_base_matches_host(
    emitter,
    destructive_mode,
    managed_mode,
    mock_check_if_base_matches_host,
    mock_provider,
    simple_base_config,
):
    """Verify the first `build_on` Base that matches the host is used for the build plan
    when building in managed mode or destructive mode."""
    build_plan = providers.create_build_plan(
        bases=simple_base_config,
        bases_indices=None,
        destructive_mode=destructive_mode,
        managed_mode=managed_mode,
        provider=mock_provider,
    )

    assert build_plan == [
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                    ],
                    "run-on": [
                        Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                    ],
                }
            ),
            build_on=Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
            bases_index=0,
            build_on_index=0,
        ),
    ]
    emitter.assert_interactions(
        [
            call("debug", "Building for 'bases[0]' as host matches 'build-on[0]'."),
        ]
    )


def test_create_build_plan_is_base_available(emitter, mock_is_base_available, mock_provider):
    """Verify the first available `build_on` Base that is used for the build plan."""
    base = [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                    Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                ],
                "run-on": [
                    Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                ],
            }
        )
    ]

    # the first Base is not available, but the second Base is available
    mock_is_base_available.side_effect = [(False, "test error message"), (True, None)]

    build_plan = providers.create_build_plan(
        bases=base,
        bases_indices=None,
        destructive_mode=False,
        managed_mode=False,
        provider=mock_provider,
    )

    # verify charmcraft will build on the second Base
    assert build_plan[0].build_on == Base(
        name="x2name", channel="x2channel", architectures=["x2arch"]
    )
    assert build_plan[0].build_on_index == 1

    emitter.assert_interactions(
        [
            call("progress", "Skipping 'bases[0].build-on[0]': test error message."),
            call("debug", "Building for 'bases[0]' as host matches 'build-on[1]'."),
        ]
    )


def test_create_build_plan_base_index_usage(
    complex_base_config,
    emitter,
    mock_is_base_available,
    mock_provider,
):
    """Verify `bases_indices` argument causes build plan to only contain matching bases."""
    build_plan = providers.create_build_plan(
        bases=complex_base_config,
        bases_indices=[1, 2],
        destructive_mode=False,
        managed_mode=False,
        provider=mock_provider,
    )

    assert build_plan == [
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                        Base(name="x4name", channel="x4channel", architectures=["x4arch"]),
                    ],
                    "run-on": [
                        Base(name="x5name", channel="x5channel", architectures=["x5arch"]),
                    ],
                }
            ),
            build_on=Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
            bases_index=1,
            build_on_index=0,
        ),
        providers.Plan(
            bases_config=BasesConfiguration(
                **{
                    "build-on": [
                        Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
                    ],
                    "run-on": [
                        Base(name="x7name", channel="x7channel", architectures=["x7arch"]),
                        Base(
                            name="x8name",
                            channel="x8channel",
                            architectures=["x8arch1", "x8arch2"],
                        ),
                    ],
                }
            ),
            build_on=Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
            bases_index=2,
            build_on_index=0,
        ),
    ]

    emitter.assert_interactions(
        [
            call("debug", "Skipping 'bases[0]' due to --base-index usage."),
            call("debug", "Building for 'bases[1]' as host matches 'build-on[0]'."),
            call("debug", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


def test_create_build_plan_no_suitable_bases(
    emitter, complex_base_config, mock_is_base_available, mock_provider
):
    """Verify an empty build plan is returned when no bases are available."""
    mock_is_base_available.return_value = (False, "test error message")

    build_plan = providers.create_build_plan(
        bases=complex_base_config,
        bases_indices=None,
        destructive_mode=False,
        managed_mode=False,
        provider=mock_provider,
    )

    assert build_plan == []

    emitter.assert_interactions(
        [
            call("progress", "Skipping 'bases[0].build-on[0]': test error message."),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[0]' configuration.",
                permanent=True,
            ),
            call("progress", "Skipping 'bases[1].build-on[0]': test error message."),
            call("progress", "Skipping 'bases[1].build-on[1]': test error message."),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                permanent=True,
            ),
            call("progress", "Skipping 'bases[2].build-on[0]': test error message."),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[2]' configuration.",
                permanent=True,
            ),
        ]
    )


def test_create_build_plan_no_bases_error(mock_provider):
    """Verify an error is raised when no bases are passed."""
    with pytest.raises(CraftError) as error:
        providers.create_build_plan(
            bases=None,
            bases_indices=None,
            destructive_mode=False,
            managed_mode=False,
            provider=mock_provider,
        )

    assert str(error.value) == "Cannot create build plan because no bases were provided."


def test_get_command_environment_minimal(monkeypatch):
    monkeypatch.setenv("IGNORE_ME", "or-im-failing")
    monkeypatch.setenv("PATH", "not-using-host-path")

    env = providers.get_command_environment(bases.ubuntu.BuilddBase)

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

    env = providers.get_command_environment(bases.ubuntu.BuilddBase)

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
    bases_index, build_on_index, project_name, target_arch, expected, tmp_path
):
    assert providers.get_instance_name(
        bases_index=bases_index,
        build_on_index=build_on_index,
        project_name=project_name,
        project_path=tmp_path,
        target_arch=target_arch,
    ) == expected.format(inode=tmp_path.stat().st_ino)


@pytest.mark.parametrize(
    "platform, snap_channel, expected_snap_channel",
    [
        ("linux", None, None),
        ("linux", "edge", "edge"),
        ("darwin", "edge", "edge"),
        # default to stable on non-linux system
        ("darwin", None, "stable"),
    ],
)
@pytest.mark.parametrize(
    "alias_ubuntu",
    [
        bases.ubuntu.BuilddBaseAlias.BIONIC,
        bases.ubuntu.BuilddBaseAlias.FOCAL,
        bases.ubuntu.BuilddBaseAlias.JAMMY,
    ],
)
def test_get_base_configuration_ubuntu(
    platform,
    snap_channel,
    expected_snap_channel,
    alias_ubuntu,
    mocker,
):
    """Verify the snapcraft snap is installed from the correct channel."""
    mocker.patch("sys.platform", platform)
    mocker.patch(
        "charmcraft.providers.get_managed_environment_snap_channel",
        return_value=snap_channel,
    )
    mocker.patch("charmcraft.providers.get_command_environment", return_value="test-env")
    mocker.patch("charmcraft.providers.get_instance_name", return_value="test-instance-name")
    mock_buildd_base = mocker.patch("craft_providers.bases.ubuntu.BuilddBase")
    mock_buildd_base.compatibility_tag = "buildd-base-v0"

    providers.get_base_configuration(alias=alias_ubuntu, instance_name="test-instance-name")

    mock_buildd_base.assert_called_with(
        alias=alias_ubuntu,
        environment="test-env",
        hostname="test-instance-name",
        snaps=[Snap(name="charmcraft", channel=expected_snap_channel, classic=True)],
        compatibility_tag="charmcraft-buildd-base-v0.0",
    )


@pytest.mark.parametrize(
    "platform, snap_channel, expected_snap_channel",
    [
        ("linux", None, None),
        ("linux", "edge", "edge"),
        ("darwin", "edge", "edge"),
        # default to stable on non-linux system
        ("darwin", None, "stable"),
    ],
)
def test_get_base_configuration_centos(
    platform,
    snap_channel,
    expected_snap_channel,
    mocker,
):
    """Verify the snapcraft snap is installed from the correct channel."""
    mocker.patch("sys.platform", platform)
    mocker.patch(
        "charmcraft.providers.get_managed_environment_snap_channel",
        return_value=snap_channel,
    )
    mocker.patch("charmcraft.providers.get_command_environment", return_value="test-env")
    mocker.patch("charmcraft.providers.get_instance_name", return_value="test-instance-name")
    mock_centos_base = mocker.patch("craft_providers.bases.centos.CentOSBase")
    mock_centos_base.compatibility_tag = "centos-base-v0"

    providers.get_base_configuration(
        alias=bases.centos.CentOSBaseAlias.SEVEN, instance_name="test-instance-name"
    )

    mock_centos_base.assert_called_with(
        alias=bases.centos.CentOSBaseAlias.SEVEN,
        environment="test-env",
        hostname="test-instance-name",
        snaps=[Snap(name="charmcraft", channel=expected_snap_channel, classic=True)],
        compatibility_tag="charmcraft-centos-base-v0.0",
    )


def test_capture_logs_from_instance_ok(emitter, mock_instance, tmp_path, mocker):
    @contextlib.contextmanager
    def fake_pull(source, missing_ok):
        assert source == pathlib.Path("/tmp/charmcraft.log")
        assert missing_ok is True
        fake_file = tmp_path / "fake.file"
        fake_file.write_text("some\nlog data\nhere")
        yield fake_file

    mocker.patch.object(mock_instance, "temporarily_pull_file", fake_pull)
    providers.capture_logs_from_instance(mock_instance)

    emitter.assert_interactions(
        [
            call("debug", "Logs captured from managed instance:"),
            call("debug", ":: some"),
            call("debug", ":: log data"),
            call("debug", ":: here"),
        ]
    )


def test_capture_logs_from_instance_not_found(emitter, mock_instance, tmp_path, mocker):
    @contextlib.contextmanager
    def fake_pull(source, missing_ok):
        yield None  # didn't find the indicated file

    mocker.patch.object(mock_instance, "temporarily_pull_file", fake_pull)
    providers.capture_logs_from_instance(mock_instance)

    emitter.assert_debug("No logs found in instance.")


def test_ensure_provider_is_available_installed_yes(mocker, fake_provider):
    """Verify provider is ensured to be available when installed (fake_provider's default)."""
    confirmation_mock = mocker.patch("charmcraft.providers.confirm_with_user")
    available_mock = mocker.patch.object(fake_provider, "ensure_provider_is_available")

    providers.ensure_provider_is_available(fake_provider)

    confirmation_mock.assert_not_called()
    available_mock.assert_called_once()


def test_ensure_provider_is_available_installed_no_user_confirms_yes(mocker, fake_provider):
    """Verify provider is ensured to be available, not installed but user chooses to install."""
    confirmation_mock = mocker.patch("charmcraft.providers.confirm_with_user", return_value=True)
    mocker.patch.object(fake_provider, "is_provider_installed", return_value=False)
    available_mock = mocker.patch.object(fake_provider, "ensure_provider_is_available")

    providers.ensure_provider_is_available(fake_provider)

    message = (
        "Provider is required but not installed. Do you wish to "
        "install provider and configure it with the defaults?"
    )
    confirmation_mock.assert_called_with(message, default=False)
    available_mock.assert_called_once()


def test_ensure_provider_is_available_installed_no_user_confirms_no(mocker, fake_provider):
    """Raise an error if not installed and the user does not choose to install it."""
    mocker.patch("charmcraft.providers.confirm_with_user", return_value=False)
    mocker.patch.object(fake_provider, "is_provider_installed", return_value=False)

    with pytest.raises(ProviderError) as error:
        providers.ensure_provider_is_available(fake_provider)

    assert error.value.brief == "Provider is required, but not installed."


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
            "name 'not-ubuntu' is not yet supported (must be 'ubuntu' or 'centos')",
        ),
        (
            "ubuntu",
            "10.04",
            ["host-arch"],
            False,
            "base 'ubuntu' channel '10.04' is not yet supported (must be 'centos 7', "
            "'ubuntu 16.04', 'ubuntu 18.04', 'ubuntu 20.04', 'ubuntu 22.04', "
            "'ubuntu 22.10', 'ubuntu 23.04' or 'ubuntu devel')",
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
    valid, reason = providers.is_base_available(base)

    assert (valid, reason) == (expected_valid, expected_reason)


def test_get_provider_default(mock_snap_config, mock_is_developer_mode, mock_is_snap):
    if sys.platform == "linux":
        provider = providers.get_provider()
        assert isinstance(provider, lxd.LXDProvider)
        assert provider.lxd_project == "charmcraft"
    else:
        assert isinstance(providers.get_provider(), multipass.MultipassProvider)


def test_get_provider_developer_mode_env(
    mock_snap_config, mock_is_developer_mode, mock_is_snap, monkeypatch
):
    mock_is_developer_mode.return_value = True
    monkeypatch.setenv("CHARMCRAFT_PROVIDER", "lxd")
    provider = providers.get_provider()
    assert isinstance(provider, lxd.LXDProvider)
    assert provider.lxd_project == "charmcraft"

    monkeypatch.setenv("CHARMCRAFT_PROVIDER", "multipass")
    assert isinstance(providers.get_provider(), multipass.MultipassProvider)


def test_get_provider_snap_config(mock_is_snap, mock_is_developer_mode, mock_snap_config):
    mock_is_snap.return_value = True

    mock_snap_config.return_value = CharmcraftSnapConfiguration(provider="lxd")
    provider = providers.get_provider()
    assert isinstance(provider, lxd.LXDProvider)
    assert provider.lxd_project == "charmcraft"

    mock_snap_config.return_value = CharmcraftSnapConfiguration(provider="multipass")
    assert isinstance(providers.get_provider(), multipass.MultipassProvider)
