# Copyright 2023-2024 Canonical Ltd.
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
"""Tests for the store service."""
import platform
from typing import cast
from unittest import mock

import craft_store
import distro
import pytest
from craft_cli.pytest_plugin import RecordingEmitter
from craft_store import models
from hypothesis import given, strategies

import charmcraft
from charmcraft import application, errors, services
from charmcraft.models.project import CharmLib
from charmcraft.store import client
from tests import get_fake_revision


@pytest.fixture
def store(service_factory) -> services.StoreService:
    store = services.StoreService(app=application.APP_METADATA, services=service_factory)
    store.client = mock.Mock(spec_set=client.Client)
    store.anonymous_client = mock.Mock(spec_set=client.AnonymousClient)
    return store


@pytest.fixture(scope="module")
def reusable_store():
    store = services.StoreService(app=application.APP_METADATA, services=None)
    store.client = mock.Mock(spec_set=craft_store.StoreClient)
    return store


def test_user_agent(store):
    assert store._user_agent == f"Charmcraft/{charmcraft.__version__} ({store._ua_system_info})"


@pytest.mark.parametrize("system", ["Windows", "Macos"])
@pytest.mark.parametrize("release", ["10", "11", "12"])
@pytest.mark.parametrize("machine", ["x86_64", "arm64", "riscv64"])
@pytest.mark.parametrize("python", ["CPython", "PyPy"])
@pytest.mark.parametrize("python_version", ["3.10", "3.12"])
def test_ua_system_info_non_linux(
    monkeypatch, store, system, release, machine, python, python_version
):
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "release", lambda: release)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(platform, "python_implementation", lambda: python)
    monkeypatch.setattr(platform, "python_version", lambda: python_version)

    assert store._ua_system_info == f"{system} {release}; {machine}; {python} {python_version}"


@pytest.mark.parametrize("machine", ["x86_64", "arm64", "riscv64"])
@pytest.mark.parametrize("python", ["CPython", "PyPy"])
@pytest.mark.parametrize("python_version", ["3.10", "3.12"])
@pytest.mark.parametrize("distro_name", ["Ubuntu", "Debian", "Something"])
@pytest.mark.parametrize("distro_version", ["1", "24.04", "version"])
def test_ua_system_info_linux(
    monkeypatch, store, machine, python, python_version, distro_name, distro_version
):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "release", lambda: "6.5.0")
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(platform, "python_implementation", lambda: python)
    monkeypatch.setattr(platform, "python_version", lambda: python_version)
    monkeypatch.setattr(distro, "name", lambda: distro_name)
    monkeypatch.setattr(distro, "version", lambda: distro_version)

    assert (
        store._ua_system_info
        == f"Linux 6.5.0; {machine}; {python} {python_version}; {distro_name} {distro_version}"
    )


def test_setup_with_error(emitter: RecordingEmitter, store):
    store.ClientClass = mock.Mock(side_effect=[craft_store.errors.NoKeyringError, "I am a store!"])

    store.setup()

    assert store.client == "I am a store!"
    emitter.assert_progress(
        "WARNING: Cannot get a keyring. Every store interaction that requires "
        "authentication will require you to log in again.",
        permanent=True,
    )


def test_get_description_default(monkeypatch, store):
    monkeypatch.setattr(platform, "node", lambda: "my-hostname")

    assert store._get_description() == "charmcraft@my-hostname"


@given(text=strategies.text())
def test_get_description_override(reusable_store, text):
    assert reusable_store._get_description(text) == text


@given(
    permissions=strategies.lists(strategies.text()),
    description=strategies.text(),
    ttl=strategies.integers(min_value=1),
    channels=strategies.lists(strategies.text()),
)
def test_login(reusable_store, permissions, description, ttl, channels):
    client = cast(mock.Mock, reusable_store.client)
    client.reset_mock(return_value=True, side_effect=True)

    reusable_store.login(
        permissions=permissions, description=description, ttl=ttl, channels=channels
    )

    client.login.assert_called_once_with(
        permissions=permissions, description=description, ttl=ttl, packages=None, channels=channels
    )


def test_login_failure(store):
    client = cast(mock.Mock, store.client)
    client.login.side_effect = craft_store.errors.CredentialsAlreadyAvailable("charmcraft", "host")

    with pytest.raises(errors.CraftError, match="Cannot login because credentials were found"):
        store.login()


def test_logout(store):
    client = cast(mock.Mock, store.client)

    store.logout()

    client.logout.assert_called_once_with()


@pytest.mark.parametrize(
    ("updates", "expected_request"),
    [
        pytest.param({}, [], id="empty"),
        pytest.param(
            {123: ["amd64", "riscv64"]},
            [
                models.CharmResourceRevisionUpdateRequest(
                    revision=123,
                    bases=[models.RequestCharmResourceBase(architectures=["amd64", "riscv64"])],
                )
            ],
        ),
        pytest.param(
            {
                123: ["amd64", "riscv64"],
                456: ["all"],
            },
            [
                models.CharmResourceRevisionUpdateRequest(
                    revision=123,
                    bases=[models.RequestCharmResourceBase(architectures=["amd64", "riscv64"])],
                ),
                models.CharmResourceRevisionUpdateRequest(
                    revision=456,
                    bases=[models.RequestCharmResourceBase(architectures=["all"])],
                ),
            ],
        ),
    ],
)
def test_set_resource_revisions_architectures_request_form(store, updates, expected_request):
    store.client.list_resource_revisions.return_value = []

    store.set_resource_revisions_architectures("my-charm", "my-file", updates)

    store.client.update_resource_revisions.assert_called_once_with(
        *expected_request,
        name="my-charm",
        resource_name="my-file",
    )


@pytest.mark.parametrize(
    ("updates", "store_response", "expected"),
    [
        ({}, [], []),
        (
            {123: ["all"]},
            [
                get_fake_revision(bases=[models.ResponseCharmResourceBase()], revision=0),
                get_fake_revision(bases=[models.ResponseCharmResourceBase()], revision=123),
            ],
            [get_fake_revision(bases=[models.ResponseCharmResourceBase()], revision=123)],
        ),
    ],
)
def test_set_resource_revisions_architectures_response_form(
    store, updates, store_response, expected
):
    store.client.list_resource_revisions.return_value = store_response

    actual = store.set_resource_revisions_architectures("my-charm", "my-file", updates)

    assert actual == expected


def test_get_credentials(monkeypatch, store):
    mock_client_class = mock.Mock(spec_set=craft_store.StoreClient)
    mock_client = mock_client_class.return_value
    monkeypatch.setattr(craft_store, "StoreClient", mock_client_class)

    store.get_credentials()

    mock_client_class.assert_called_once_with(
        application_name="charmcraft",
        base_url=mock.ANY,
        storage_base_url=mock.ANY,
        endpoints=mock.ANY,
        environment_auth=None,
        user_agent=store._user_agent,
        ephemeral=True,
    )
    mock_client.login.assert_called_once_with(
        permissions=mock.ANY,
        description=store._get_description(),
        ttl=mock.ANY,
        packages=None,
        channels=None,
    )


@pytest.mark.parametrize(
    ("libs", "expected_call"),
    [
        ([], []),
        (
            [CharmLib(lib="my_charm.my_lib", version="1")],
            [{"charm-name": "my-charm", "library-name": "my_lib", "api": 1}],
        ),
        (
            [CharmLib(lib="my_charm.my_lib", version="1.0")],
            [{"charm-name": "my-charm", "library-name": "my_lib", "api": 1, "patch": 0}],
        ),
    ],
)
def test_fetch_libraries_metadata(monkeypatch, store, libs, expected_call):

    store.get_libraries_metadata(libs)

    store.anonymous_client.fetch_libraries_metadata.assert_called_once_with(expected_call)
