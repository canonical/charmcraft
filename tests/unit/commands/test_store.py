# Copyright 2024 Canonical Ltd.
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
"""Unit tests for store commands."""

import argparse
import datetime
import pathlib
import textwrap
import types
from unittest import mock

import craft_application
import craft_cli.pytest_plugin
import craft_store
import pytest
from craft_cli import CraftError
from craft_store import models, publisher
from craft_store.publisher import Releases

from charmcraft import errors, store
from charmcraft.application import commands
from charmcraft.application.commands import SetResourceArchitecturesCommand
from charmcraft.application.commands import store as store_commands
from charmcraft.application.commands.store import (
    FetchLibs,
    LoginCommand,
    PublishLibCommand,
)
from charmcraft.application.main import APP_METADATA
from charmcraft.models.project import CharmLib
from charmcraft.store.models import Library
from charmcraft.utils import cli
from tests import get_fake_revision

BASIC_CHARMCRAFT_YAML = """\
type: charm
"""


def test_login_basic_no_export(service_factory, mock_store_client):
    cmd = LoginCommand({"app": APP_METADATA, "services": service_factory})

    cmd.run(
        argparse.Namespace(
            charm=None,
            bundle=None,
            channel=None,
            permission=None,
            ttl=None,
            export=None,
        )
    )


@pytest.mark.parametrize("charm", [None, ["my-charm"]])
@pytest.mark.parametrize("bundle", [None, ["my-bundle"]])
@pytest.mark.parametrize("channel", [None, ["edge", "latest/stable"]])
@pytest.mark.parametrize("permission", [None, [], ["package-manage"]])
@pytest.mark.parametrize("ttl", [None, 0, 2**65])
def test_login_export(
    monkeypatch,
    service_factory,
    mock_store_client,
    charm,
    bundle,
    channel,
    permission,
    ttl,
):
    mock_client_cls = mock.Mock(return_value=mock_store_client)
    monkeypatch.setattr(craft_store, "StoreClient", mock_client_cls)
    mock_store_client.login.return_value = "Some store credentials"
    cmd = LoginCommand({"app": APP_METADATA, "services": service_factory})

    cmd.run(
        argparse.Namespace(
            charm=charm,
            bundle=bundle,
            channel=channel,
            permission=permission,
            ttl=ttl,
            export=pathlib.Path("charmhub.login"),
        )
    )

    assert pathlib.Path("charmhub.login").read_text() == "Some store credentials"
    mock_store_client.login.assert_called_once()


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([], []),
        (
            [
                get_fake_revision(
                    revision=123,
                    updated_at=datetime.datetime(1900, 1, 1),
                    bases=[models.ResponseCharmResourceBase()],
                )
            ],
            [
                {
                    "revision": 123,
                    "updated_at": "1900-01-01T00:00:00",
                    "architectures": ["all"],
                }
            ],
        ),
    ],
)
def test_set_resource_architectures_output_json(emitter, updates, expected):
    SetResourceArchitecturesCommand.write_output(cli.OutputFormat.JSON, updates)

    emitter.assert_json_output(expected)


def test_publish_lib_error(monkeypatch, new_path: pathlib.Path) -> None:
    mock_service_factory = mock.Mock(spec=craft_application.ServiceFactory)
    mock_service_factory.get.return_value.get.return_value.name = "test-project"
    lib_path = new_path / "lib/charms/test_project/v0/my_lib.py"
    lib_path.parent.mkdir(parents=True)
    lib_path.write_text("LIBAPI=0\nLIBID='blah'\nLIBPATCH=1")

    mock_store = mock.Mock()
    mock_store.return_value.get_libraries_tips.return_value = {
        ("blah", 0): Library(
            charm_name="test-project",
            lib_id="blah",
            lib_name="my_lib",
            api=0,
            patch=2,
            content=None,
            content_hash="",
        ),
    }
    monkeypatch.setattr(store_commands, "Store", mock_store)

    cmd = PublishLibCommand({"app": APP_METADATA, "services": mock_service_factory})

    assert (
        cmd.run(
            argparse.Namespace(
                library="charms.test-project.v0.my_lib",
                format=False,
            )
        )
        == 1
    )


def test_publish_lib_same_is_noop(monkeypatch, new_path: pathlib.Path) -> None:
    # Publishing the same version of a library with the same hash should not result
    # in an error return.
    mock_service_factory = mock.Mock(spec=craft_application.ServiceFactory)
    mock_service_factory.get.return_value.get.return_value.name = "test-project"
    lib_path = new_path / "lib/charms/test_project/v0/my_lib.py"
    lib_path.parent.mkdir(parents=True)
    lib_path.write_text("LIBAPI=0\nLIBID='blah'\nLIBPATCH=1")

    mock_store = mock.Mock()
    mock_store.return_value.get_libraries_tips.return_value = {
        ("blah", 0): Library(
            charm_name="test-project",
            lib_id="blah",
            lib_name="my_lib",
            api=0,
            patch=1,
            content=None,
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
    }
    monkeypatch.setattr(store_commands, "Store", mock_store)

    cmd = PublishLibCommand({"app": APP_METADATA, "services": mock_service_factory})

    assert (
        cmd.run(
            argparse.Namespace(
                library="charms.test-project.v0.my_lib",
                format=False,
            )
        )
        == 0
    )


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([], "No revisions updated."),
        (
            [
                get_fake_revision(
                    revision=123,
                    updated_at=datetime.datetime(1900, 1, 1),
                    bases=[models.ResponseCharmResourceBase()],
                )
            ],
            textwrap.dedent(
                """\
                  Revision  Updated At            Architectures
                ----------  --------------------  ---------------
                       123  1900-01-01T00:00:00Z  all"""
            ),
        ),
    ],
)
def test_set_resource_architectures_output_table(emitter, updates, expected):
    SetResourceArchitecturesCommand.write_output(cli.OutputFormat.TABLE, updates)

    emitter.assert_message(expected)


def test_fetch_libs_no_charm_libs(
    emitter: craft_cli.pytest_plugin.RecordingEmitter, service_factory
):
    fetch_libs = FetchLibs({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(errors.LibraryError) as exc_info:
        fetch_libs.run(argparse.Namespace())

    assert exc_info.value.resolution == "Add a 'charm-libs' section to charmcraft.yaml."


@pytest.mark.parametrize(
    ("libs", "expected"),
    [
        (
            [CharmLib(lib="mysql.mysql", version="1")],
            textwrap.dedent(
                """\
                Could not find the following libraries on charmhub:
                - lib: mysql.mysql
                  version: '1'
                """
            ),
        ),
        (
            [
                CharmLib(lib="mysql.mysql", version="1"),
                CharmLib(lib="some_charm.lib", version="1.2"),
            ],
            textwrap.dedent(
                """\
                Could not find the following libraries on charmhub:
                - lib: mysql.mysql
                  version: '1'
                - lib: some-charm.lib
                  version: '1.2'
                """
            ),
        ),
    ],
)
def test_fetch_libs_missing_from_store(service_factory, libs, expected):
    project = service_factory.get("project").get()
    project.charm_libs = libs
    service_factory.get(
        "store"
    ).anonymous_client.fetch_libraries_metadata.return_value = []
    fetch_libs = FetchLibs({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(errors.CraftError) as exc_info:
        fetch_libs.run(argparse.Namespace())

    assert exc_info.value.args[0] == expected


@pytest.mark.parametrize(
    ("libs", "store_libs", "dl_lib", "expected"),
    [
        (
            [CharmLib(lib="mysql.backups", version="1")],
            [
                store.models.Library(
                    charm_name="mysql",
                    lib_name="backups",
                    lib_id="ididid",
                    api=1,
                    patch=2,
                    content=None,
                    content_hash="hashhashhash",
                )
            ],
            store.models.Library(
                charm_name="mysql",
                lib_name="backups",
                lib_id="ididid",
                api=1,
                patch=2,
                content=None,
                content_hash="hashhashhash",
            ),
            "Store returned no content for 'mysql.backups'",
        ),
    ],
)
def test_fetch_libs_no_content(
    new_path, service_factory, libs, store_libs, dl_lib, expected
):
    service_factory.get("project").get().charm_libs = libs
    service_factory.store.anonymous_client.fetch_libraries_metadata.return_value = (
        store_libs
    )
    service_factory.store.anonymous_client.get_library.return_value = dl_lib
    fetch_libs = FetchLibs({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(errors.CraftError, match=expected) as exc_info:
        fetch_libs.run(argparse.Namespace())

    assert exc_info.value.args[0] == expected


@pytest.mark.parametrize(
    ("libs", "store_libs", "dl_lib", "expected"),
    [
        (
            [CharmLib(lib="mysql.backups", version="1")],
            [
                store.models.Library(
                    charm_name="mysql",
                    lib_name="backups",
                    lib_id="ididid",
                    api=1,
                    patch=2,
                    content=None,
                    content_hash="hashhashhash",
                )
            ],
            store.models.Library(
                charm_name="mysql",
                lib_name="backups",
                lib_id="ididid",
                api=1,
                patch=2,
                content="I am a library.",
                content_hash="hashhashhash",
            ),
            "Store returned no content for 'mysql.backups'",
        ),
    ],
)
def test_fetch_libs_success(
    new_path, emitter, service_factory, libs, store_libs, dl_lib, expected
) -> None:
    service_factory.get("project").get().charm_libs = libs
    service_factory.store.anonymous_client.fetch_libraries_metadata.return_value = (
        store_libs
    )
    service_factory.store.anonymous_client.get_library.return_value = dl_lib
    fetch_libs = FetchLibs({"app": APP_METADATA, "services": service_factory})

    fetch_libs.run(argparse.Namespace())

    emitter.assert_progress("Getting library metadata from charmhub")
    emitter.assert_message("Downloaded 1 charm libraries.")


def test_promote_no_track_inference_noninteractive(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway,
):
    mock_publisher_gateway.get_package_metadata.return_value = types.SimpleNamespace(
        default_track="latest"
    )

    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel="candidate",
        to_channel="stable",
        yes=True,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(CraftError, match="Channels must be fully defined"):
        cmd.run(parsed_args)


@pytest.mark.parametrize(
    "channel",
    ["latest/stable", "latest/candidate", "latest/beta", "latest/edge", "3/edge"],
)
def test_promote_to_same_channel(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    channel: str,
):
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=channel,
        to_channel=channel,
        yes=True,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(
        CraftError, match="Cannot promote from a channel to the same channel."
    ):
        cmd.run(parsed_args)


@pytest.mark.parametrize(
    ("from_channel", "to_channel"),
    [
        ("candidate", "latest/candidate"),
        ("stable", "latest/stable"),
        ("latest/candidate", "candidate"),
        ("latest/stable", "stable"),
    ],
)
def test_promote_infers_channel(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    from_channel: str,
    to_channel: str,
):
    # This test works by checking that the channels become the same after inferring
    # the default track "latest" and then checking that the channels are the same.
    mock_publisher_gateway.get_package_metadata.return_value = types.SimpleNamespace(
        default_track="latest"
    )

    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=from_channel,
        to_channel=to_channel,
        yes=False,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(
        CraftError, match=r"^Cannot promote from a channel to the same channel\.$"
    ):
        cmd.run(parsed_args)


@pytest.mark.parametrize(
    ("from_channel", "to_channel"),
    [
        ("latest/stable", "latest/candidate"),
        ("latest/stable", "latest/beta"),
        ("latest/candidate", "latest/beta"),
        ("latest/beta", "latest/edge"),
    ],
)
def test_promote_not_demote(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    from_channel: str,
    to_channel: str,
):
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=from_channel,
        to_channel=to_channel,
        yes=True,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(
        CraftError,
        match=r"^Target channel \([a-z/]+\) must be lower risk than the source channel \([a-z/]+\)\.$",
    ) as exc_info:
        cmd.run(parsed_args)

    assert (
        exc_info.value.resolution
        == f"Did you mean: charmcraft promote --from-channel={to_channel} --to-channel={from_channel}"
    )


@pytest.mark.parametrize(
    ("from_channel", "to_channel"),
    [
        ("latest/candidate", "3/stable"),
        ("latest/beta", "3/candidate"),
        ("latest/edge", "3/beta"),
    ],
)
def test_promote_cross_track_cannot_be_different_risk(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    from_channel: str,
    to_channel: str,
):
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=from_channel,
        to_channel=to_channel,
        yes=True,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    with pytest.raises(
        CraftError,
        match=r"^Cross-track promotion can only occur at the same risk level\.$",
    ):
        cmd.run(parsed_args)


@pytest.mark.parametrize(
    ("from_channel", "to_channel"),
    [
        ("latest/candidate", "3/candidate"),
    ],
)
def test_promote_cross_track_defaults_no(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    from_channel: str,
    to_channel: str,
):
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=from_channel,
        to_channel=to_channel,
        yes=False,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    assert cmd.run(parsed_args) == 64

    emitter.assert_message("Cancelling.")


@pytest.mark.parametrize(
    ("from_channel", "to_channel"),
    [
        ("latest/candidate", "latest/stable"),
    ],
)
def test_promote_defaults_no(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
    from_channel: str,
    to_channel: str,
):
    mock_publisher_gateway.list_releases.return_value = Releases(
        channel_map=[], package=publisher.Package(channels=[]), revisions=[]
    )
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel=from_channel,
        to_channel=to_channel,
        yes=False,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    assert cmd.run(parsed_args) == 1

    emitter.assert_message("Channel promotion cancelled.")


def test_promote_revisions(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: craft_application.ServiceFactory,
    mock_publisher_gateway: mock.Mock,
):
    mock_publisher_gateway.list_releases.return_value = Releases(
        channel_map=[], package=publisher.Package(channels=[]), revisions=[]
    )
    mock_publisher_gateway.release.return_value = []
    parsed_args = argparse.Namespace(
        name="my-charm",
        from_channel="latest/candidate",
        to_channel="latest/stable",
        yes=True,
    )
    cmd = commands.PromoteCommand({"app": APP_METADATA, "services": service_factory})

    assert cmd.run(parsed_args) == 0

    emitter.assert_message(
        "0 revisions promoted from latest/candidate to latest/stable"
    )
