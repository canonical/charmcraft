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
from unittest import mock

import craft_cli.pytest_plugin
import craft_store
import pytest
from craft_store import models

from charmcraft import errors, store
from charmcraft.application.commands import SetResourceArchitecturesCommand
from charmcraft.application.commands.store import FetchLibs, LoginCommand
from charmcraft.application.main import APP_METADATA
from charmcraft.models.project import CharmLib
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
    monkeypatch, service_factory, mock_store_client, charm, bundle, channel, permission, ttl
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
            [{"revision": 123, "updated_at": "1900-01-01T00:00:00", "architectures": ["all"]}],
        ),
    ],
)
def test_set_resource_architectures_output_json(emitter, updates, expected):
    SetResourceArchitecturesCommand.write_output(cli.OutputFormat.JSON, updates)

    emitter.assert_json_output(expected)


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
    service_factory.project.charm_libs = libs
    service_factory.store.anonymous_client.fetch_libraries_metadata.return_value = []
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
def test_fetch_libs_no_content(new_path, service_factory, libs, store_libs, dl_lib, expected):
    service_factory.project.charm_libs = libs
    service_factory.store.anonymous_client.fetch_libraries_metadata.return_value = store_libs
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
    service_factory.project.charm_libs = libs
    service_factory.store.anonymous_client.fetch_libraries_metadata.return_value = store_libs
    service_factory.store.anonymous_client.get_library.return_value = dl_lib
    fetch_libs = FetchLibs({"app": APP_METADATA, "services": service_factory})

    fetch_libs.run(argparse.Namespace())

    emitter.assert_progress("Getting library metadata from charmhub")
    emitter.assert_message("Downloaded 1 charm libraries.")
