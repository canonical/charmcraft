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

import os
import subprocess
from unittest import mock
from unittest.mock import call

import pytest
from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

from charmcraft import providers
from charmcraft.config import Base


@pytest.fixture(autouse=True)
def bypass_buildd_base_setup(monkeypatch):
    """Patch out inherited setup steps."""
    monkeypatch.setattr(bases.BuilddBase, "setup", lambda *args, **kwargs: None)


@pytest.fixture
def mock_executor():
    yield mock.Mock(spec=Executor)


@pytest.fixture
def mock_lxd(monkeypatch):
    with mock.patch("charmcraft.providers.lxd", autospec=True) as mock_lxd:
        yield mock_lxd


@pytest.fixture
def mock_inject():
    with mock.patch(
        "craft_providers.actions.snap_installer.inject_from_host"
    ) as mock_inject:
        yield mock_inject


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch):
    monkeypatch.setattr(os, "environ", {})


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

    assert config.compatibility_tag == "charmcraft-buildd-base-v0.0"


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


def test_get_command_environment_minimal(monkeypatch):
    monkeypatch.setenv("IGNORE_ME", "or-im-failing")
    monkeypatch.setenv("PATH", "not-using-host-path")

    env = providers.get_command_environment()

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

    env = providers.get_command_environment()

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
        (0, 0, "mycharm", "test-arch1", "charmcraft-mycharm-0-0-test-arch1"),
        (
            1,
            2,
            "my-other-charm",
            "test-arch2",
            "charmcraft-my-other-charm-1-2-test-arch2",
        ),
    ],
)
def test_get_instance_name(
    bases_index, build_on_index, project_name, target_arch, expected
):
    assert (
        providers.get_instance_name(
            bases_index=bases_index,
            build_on_index=build_on_index,
            project_name=project_name,
            target_arch=target_arch,
        )
        == expected
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
def test_is_base_providable(
    monkeypatch, name, channel, architectures, expected_valid, expected_reason
):
    monkeypatch.setattr(providers, "get_host_architecture", lambda: "host-arch")
    base = Base(name=name, channel=channel, architectures=architectures)

    valid, reason = providers.is_base_providable(base)

    assert (valid, reason) == (expected_valid, expected_reason)
