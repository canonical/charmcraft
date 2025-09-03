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

import datetime
import platform
from typing import cast
from unittest import mock

import craft_store
import craft_store.errors
import distro
import pytest
import requests
from craft_cli.pytest_plugin import RecordingEmitter
from craft_store import models, publisher
from hypothesis import given, strategies

import charmcraft
from charmcraft import application, errors
from charmcraft.models.project import CharmLib
from charmcraft.services.store import StoreService
from charmcraft.store import client
from tests import get_fake_revision


@pytest.fixture
def store(service_factory, mock_store_anonymous_client) -> StoreService:
    store = StoreService(app=application.APP_METADATA, services=service_factory)
    store.client = mock.Mock(spec_set=client.Client)
    store.anonymous_client = mock_store_anonymous_client
    return store


@pytest.fixture(scope="module")
def reusable_store():
    store = StoreService(app=application.APP_METADATA, services=None)
    store.client = mock.Mock(spec_set=craft_store.StoreClient)
    store._publisher = mock.Mock(spec_set=craft_store.PublisherGateway)
    return store


def test_user_agent(store):
    assert (
        store._user_agent
        == f"Charmcraft/{charmcraft.__version__} ({store._ua_system_info})"
    )


@pytest.mark.parametrize("system", ["Macos"])
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

    assert (
        store._ua_system_info
        == f"{system} {release}; {machine}; {python} {python_version}"
    )


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
    store.ClientClass = mock.Mock(
        side_effect=[craft_store.errors.NoKeyringError, "I am a store!"]
    )

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
        permissions=permissions,
        description=description,
        ttl=ttl,
        packages=None,
        channels=channels,
    )


def test_login_failure(store):
    client = cast(mock.Mock, store.client)
    client.login.side_effect = craft_store.errors.CredentialsAlreadyAvailable(
        "charmcraft", "host"
    )

    with pytest.raises(
        errors.CraftError, match="Cannot login because credentials were found"
    ):
        store.login()


def test_logout(store):
    client = cast(mock.Mock, store.client)

    store.logout()

    client.logout.assert_called_once_with()


def test_create_tracks(reusable_store: StoreService):
    mock_create = cast(mock.Mock, reusable_store._publisher.create_tracks)
    mock_md = cast(mock.Mock, reusable_store._publisher.get_package_metadata)
    user_track: publisher.CreateTrackRequest = {
        "name": "my-track",
        "automatic-phasing-percentage": None,
    }
    created_at = {"created-at": datetime.datetime.now()}
    return_track = publisher.Track.unmarshal(user_track | created_at)
    mock_md.return_value = publisher.RegisteredName.unmarshal(
        {
            "id": "mentalism",
            "private": False,
            "publisher": {"id": "EliBosnick"},
            "status": "hungry",
            "store": "charmhub",
            "type": "charm",
            "tracks": [
                return_track,
                publisher.Track.unmarshal(
                    {
                        "name": "latest",
                        "automatic-phasing-percentage": None,
                    }
                    | created_at
                ),
            ],
        }
    )

    assert reusable_store.create_tracks("my-name", user_track) == [return_track]
    mock_create.assert_called_once_with("my-name", user_track)


@pytest.mark.parametrize(
    ("updates", "expected_request"),
    [
        pytest.param({}, [], id="empty"),
        pytest.param(
            {123: ["amd64", "riscv64"]},
            [
                models.CharmResourceRevisionUpdateRequest(
                    revision=123,
                    bases=[
                        models.RequestCharmResourceBase(
                            architectures=["amd64", "riscv64"]
                        )
                    ],
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
                    bases=[
                        models.RequestCharmResourceBase(
                            architectures=["amd64", "riscv64"]
                        )
                    ],
                ),
                models.CharmResourceRevisionUpdateRequest(
                    revision=456,
                    bases=[models.RequestCharmResourceBase(architectures=["all"])],
                ),
            ],
        ),
    ],
)
def test_set_resource_revisions_architectures_request_form(
    store, updates, expected_request
):
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
                get_fake_revision(
                    bases=[models.ResponseCharmResourceBase()], revision=0
                ),
                get_fake_revision(
                    bases=[models.ResponseCharmResourceBase()], revision=123
                ),
            ],
            [
                get_fake_revision(
                    bases=[models.ResponseCharmResourceBase()], revision=123
                )
            ],
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


@given(name=strategies.text())
def test_get_package_metadata(reusable_store: StoreService, name: str):
    mock_get = cast(mock.Mock, reusable_store._publisher.get_package_metadata)
    mock_get.reset_mock()  # Hypothesis runs this multiple times with the same fixture.

    reusable_store.get_package_metadata(name)

    mock_get.assert_called_once_with(name)


@pytest.mark.parametrize("requests", [[], [{}]])
def test_release(reusable_store: StoreService, requests):
    name = "my-charm"
    mock_release = cast(mock.Mock, reusable_store._publisher.release)
    mock_release.reset_mock()

    reusable_store.release(name, requests)

    mock_release.assert_called_once_with(name, requests=requests)


@pytest.mark.parametrize(
    ("store_response", "expected"),
    [
        pytest.param(
            publisher.Releases(
                channel_map=[], package=publisher.Package(channels=[]), revisions=[]
            ),
            [],
            id="empty",
        ),
        pytest.param(
            publisher.Releases(
                channel_map=[
                    publisher.ChannelMap(
                        base=publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        ),
                        channel="latest/edge",
                        revision=1,
                        when=datetime.datetime(2020, 1, 1),
                    )
                ],
                package=publisher.Package(channels=[]),
                revisions=[
                    publisher.CharmRevision(
                        revision=1,
                        bases=[
                            publisher.Base(
                                name="ubuntu", channel="25.10", architecture="riscv64"
                            )
                        ],
                        version="1",
                        status="peachy",
                        created_at=datetime.datetime(2020, 1, 1),
                        size=0,
                    )
                ],
            ),
            [
                {
                    "revision": 1,
                    "bases": [
                        publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        )
                    ],
                    "resources": [],
                    "version": "1",
                }
            ],
            id="basic",
        ),
        pytest.param(
            publisher.Releases(
                channel_map=[
                    publisher.ChannelMap(
                        base=publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        ),
                        channel="latest/edge",
                        revision=1,
                        when=datetime.datetime(2020, 1, 1),
                        resources=[
                            publisher.Resource(name="file", revision=2, type="file"),
                            publisher.Resource(
                                name="rock", revision=3, type="oci-image"
                            ),
                        ],
                    )
                ],
                package=publisher.Package(channels=[]),
                revisions=[
                    publisher.CharmRevision(
                        revision=1,
                        bases=[
                            publisher.Base(
                                name="ubuntu", channel="25.10", architecture="riscv64"
                            )
                        ],
                        version="1",
                        status="peachy",
                        created_at=datetime.datetime(2020, 1, 1),
                        size=0,
                    )
                ],
            ),
            [
                {
                    "revision": 1,
                    "bases": [
                        publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        )
                    ],
                    "resources": [
                        {"name": "file", "revision": 2},
                        {"name": "rock", "revision": 3},
                    ],
                    "version": "1",
                }
            ],
            id="resources",
        ),
        pytest.param(
            publisher.Releases(
                channel_map=[
                    publisher.ChannelMap(
                        base=publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        ),
                        channel="latest/edge",
                        revision=1,
                        when=datetime.datetime(2020, 1, 1),
                        resources=[
                            publisher.Resource(name="file", revision=2, type="file"),
                            publisher.Resource(
                                name="rock", revision=3, type="oci-image"
                            ),
                        ],
                    ),
                    publisher.ChannelMap(
                        base=publisher.Base(
                            name="ubuntu", channel="25.11", architecture="riscv64"
                        ),
                        channel="latest/edge",
                        revision=1,
                        when=datetime.datetime(2020, 1, 1),
                        resources=[
                            publisher.Resource(name="file", revision=2, type="file"),
                            publisher.Resource(
                                name="rock", revision=3, type="oci-image"
                            ),
                        ],
                    ),
                ],
                package=publisher.Package(channels=[]),
                revisions=[
                    publisher.CharmRevision(
                        revision=1,
                        bases=[
                            publisher.Base(
                                name="ubuntu", channel="25.10", architecture="riscv64"
                            ),
                            publisher.Base(
                                name="ubuntu", channel="25.11", architecture="riscv64"
                            ),
                        ],
                        version="1",
                        status="peachy",
                        created_at=datetime.datetime(2020, 1, 1),
                        size=0,
                    )
                ],
            ),
            [
                {
                    "revision": 1,
                    "bases": [
                        publisher.Base(
                            name="ubuntu", channel="25.10", architecture="riscv64"
                        ),
                        publisher.Base(
                            name="ubuntu", channel="25.11", architecture="riscv64"
                        ),
                    ],
                    "resources": [
                        {"name": "file", "revision": 2},
                        {"name": "rock", "revision": 3},
                    ],
                    "version": "1",
                }
            ],
            id="multiple-bases",
        ),
    ],
)
def test_get_revisions_on_channel(
    reusable_store: StoreService, store_response, expected
):
    name = "my-charm"
    channel = "latest/edge"
    mock_list = cast(mock.Mock, reusable_store._publisher.list_releases)
    mock_list.return_value = store_response

    actual = reusable_store.get_revisions_on_channel(name, channel)

    assert actual == expected


@pytest.mark.parametrize(
    ("channel", "candidates", "expected"),
    [
        ("latest/stable", [], []),
        (
            "latest/edge",
            [{"revision": 1, "resources": []}],
            [{"channel": "latest/edge", "revision": 1, "resources": []}],
        ),
        (
            "latest/beta",
            [
                {"revision": 1, "resources": [{"name": "boo", "revision": 1}]},
                {"revision": 2, "resources": [{"name": "hoo", "revision": 2}]},
            ],
            [
                {
                    "channel": "latest/beta",
                    "revision": 1,
                    "resources": [{"name": "boo", "revision": 1}],
                },
                {
                    "channel": "latest/beta",
                    "revision": 2,
                    "resources": [{"name": "hoo", "revision": 2}],
                },
            ],
        ),
    ],
)
def test_release_promotion_candidates(
    reusable_store: StoreService, channel, candidates, expected
):
    mock_release = cast(mock.Mock, reusable_store._publisher.release)
    mock_release.reset_mock()

    assert (
        reusable_store.release_promotion_candidates("my-charm", channel, candidates)
        == mock_release.return_value
    )

    mock_release.assert_called_once_with("my-charm", requests=expected)


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
            [
                {
                    "charm-name": "my-charm",
                    "library-name": "my_lib",
                    "api": 1,
                    "patch": 0,
                }
            ],
        ),
    ],
)
def test_fetch_libraries_metadata(monkeypatch, store, libs, expected_call):
    store.get_libraries_metadata(libs)

    store.anonymous_client.fetch_libraries_metadata.assert_called_once_with(
        expected_call
    )


def test_get_libraries_metadata_name_error(
    monkeypatch, store: StoreService, mock_store_anonymous_client: mock.Mock
) -> None:
    bad_response = requests.Response()
    bad_response.status_code = 400
    bad_response._content = b'{"error-list": [{"code": null, "message": "Items need to include \'library_id\' or \'package_id\'"}]}'
    mock_store_anonymous_client.fetch_libraries_metadata.side_effect = (
        craft_store.errors.StoreServerError(bad_response)
    )

    with pytest.raises(errors.LibraryError, match="One or more declared"):
        store.get_libraries_metadata([CharmLib(lib="boop.snoot", version="-1")])
