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
"""Integration tests for store commands."""

import argparse
import datetime
import json
import pathlib
import re
from unittest import mock

import craft_cli.pytest_plugin
import pytest
from craft_store import publisher

from charmcraft import errors, utils
from charmcraft.application.commands import FetchLibCommand
from charmcraft.application.commands.store import CreateTrack
from tests import factory

OPERATOR_LIBS_LINUX_APT_ID = "7c3dbc9c2ad44a47bd6fcb25caa270e5"
OPERATOR_LIBS_LINUX_SNAP_ID = "05394e5893f94f2d90feb7cbe6b633cd"
MYSQL_MYSQL_ID = "8c1428f06b1b4ec8bf98b7d980a38a8c"


# region fetch-lib tests
@pytest.mark.slow
@pytest.mark.parametrize("formatted", [None, "json"])
def test_fetchlib_simple_downloaded(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    new_path: pathlib.Path,
    config,
    formatted: str | None,
):
    """Happy path fetching the lib for the first time (downloading it)."""
    saved_file = new_path / utils.get_lib_path("operator_libs_linux", "apt", 0)
    args = argparse.Namespace(
        library="charms.operator_libs_linux.v0.apt", format=formatted
    )
    FetchLibCommand(config).run(args)

    assert saved_file.exists()

    message = emitter.interactions[-1].args[1]

    if formatted:
        message_dict = json.loads(message)[0]
        assert isinstance(message_dict["fetched"]["patch"], int)
        assert len(message_dict["fetched"]["content_hash"]) == 64  # sha256 hash
        del message_dict["fetched"]
        assert message_dict == {
            "charm_name": "operator-libs-linux",
            "library_name": "apt",
            "library_id": OPERATOR_LIBS_LINUX_APT_ID,
            "api": 0,
        }
    else:
        assert re.match(
            r"Library charms\.operator_libs_linux\.v0\.apt version 0.[0-9]+ downloaded.",
            message,
        )

    lib = utils.get_lib_info(lib_path=saved_file)
    assert lib.api == 0
    assert lib.charm_name == "operator-libs-linux"
    assert lib.lib_name == "apt"
    assert lib.lib_id == OPERATOR_LIBS_LINUX_APT_ID
    assert lib.patch > 1


@pytest.mark.slow
def test_fetchlib_simple_updated(
    emitter: craft_cli.pytest_plugin.RecordingEmitter, new_path: pathlib.Path, config
):
    """Happy path fetching the lib for Nth time (updating it)."""
    content, content_hash = factory.create_lib_filepath(
        "operator-libs-linux", "apt", api=0, patch=1, lib_id=OPERATOR_LIBS_LINUX_APT_ID
    )

    args = argparse.Namespace(library="charms.operator_libs_linux.v0.apt", format=None)
    FetchLibCommand(config).run(args)

    message = emitter.interactions[-1].args[1]

    assert re.match(
        r"Library charms\.operator_libs_linux\.v0\.apt updated to version 0\.[0-9]+\.",
        message,
    )

    saved_file = new_path / utils.get_lib_path("operator_libs_linux", "apt", 0)
    lib = utils.get_lib_info(lib_path=saved_file)
    assert lib.api == 0
    assert lib.charm_name == "operator-libs-linux"
    assert lib.lib_name == "apt"
    assert lib.lib_id == OPERATOR_LIBS_LINUX_APT_ID
    assert lib.patch > 1


@pytest.mark.slow
@pytest.mark.parametrize("formatted", [None, "json"])
def test_fetchlib_all(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    new_path: pathlib.Path,
    config,
    formatted: str | None,
):
    """Update all the libraries found in disk."""
    factory.create_lib_filepath(
        "operator-libs-linux",
        "snap",
        api=0,
        patch=1,
        lib_id=OPERATOR_LIBS_LINUX_SNAP_ID,
    )
    factory.create_lib_filepath("mysql", "mysql", api=0, patch=1, lib_id=MYSQL_MYSQL_ID)

    args = argparse.Namespace(library=None, format=formatted)
    FetchLibCommand(config).run(args)
    message = emitter.interactions[-1].args[1]

    if formatted:
        message_list = json.loads(message)
        for message_dict in message_list:
            assert isinstance(message_dict["fetched"]["patch"], int)
            assert len(message_dict["fetched"]["content_hash"]) == 64  # sha256 hash
            del message_dict["fetched"]
        assert message_list == [
            {
                "charm_name": "mysql",
                "library_name": "mysql",
                "library_id": MYSQL_MYSQL_ID,
                "api": 0,
            },
            {
                "charm_name": "operator-libs-linux",
                "library_name": "snap",
                "library_id": OPERATOR_LIBS_LINUX_SNAP_ID,
                "api": 0,
            },
        ]
    else:
        assert re.match(
            r"Library charms\.[a-z_]+\.v0\.[a-z]+ updated to version 0\.[0-9]+\.",
            message,
        )

    saved_file = new_path / utils.get_lib_path("operator_libs_linux", "snap", 0)
    lib = utils.get_lib_info(lib_path=saved_file)
    assert lib.api == 0
    assert lib.charm_name == "operator-libs-linux"
    assert lib.lib_name == "snap"
    assert lib.lib_id == OPERATOR_LIBS_LINUX_SNAP_ID
    assert lib.patch > 1

    saved_file = new_path / utils.get_lib_path("mysql", "mysql", 0)
    lib = utils.get_lib_info(lib_path=saved_file)
    assert lib.api == 0
    assert lib.charm_name == "mysql"
    assert lib.lib_name == "mysql"
    assert lib.lib_id == MYSQL_MYSQL_ID
    assert lib.patch > 1


@pytest.mark.slow
@pytest.mark.parametrize("formatted", [None, "json"])
def test_fetchlib_store_not_found(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    new_path: pathlib.Path,
    config,
    formatted: str | None,
) -> None:
    """The indicated library is not found in the store."""
    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)

    with pytest.raises(errors.LibraryError) as exc_info:
        FetchLibCommand(config).run(args)

    assert exc_info.value.args[0] == (
        "Library charms.testcharm.v0.testlib not found in Charmhub."
    )


@pytest.mark.slow
@pytest.mark.parametrize("formatted", [None, "json"])
def test_fetchlib_store_is_old(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    new_path: pathlib.Path,
    config,
    formatted: str | None,
):
    """The store has an older version that what is found locally."""
    factory.create_lib_filepath(
        "mysql", "mysql", api=0, patch=2**63, lib_id=MYSQL_MYSQL_ID
    )

    args = argparse.Namespace(library="charms.mysql.v0.mysql", format=formatted)
    FetchLibCommand(config).run(args)

    error_message = (
        "Library charms.mysql.v0.mysql has local changes, cannot be updated."
    )
    if formatted:
        expected = [
            {
                "charm_name": "mysql",
                "library_name": "mysql",
                "library_id": MYSQL_MYSQL_ID,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(  # pyright: ignore[reportAttributeAccessIssue]
            expected
        )
    else:
        emitter.assert_message(error_message)


@pytest.mark.slow
def test_fetchlib_store_same_versions_same_hash(
    emitter: craft_cli.pytest_plugin.RecordingEmitter, new_path: pathlib.Path, config
):
    """The store situation is the same than locally."""
    args = argparse.Namespace(library="charms.operator_libs_linux.v0.snap", format=None)
    # This run is a setup run
    FetchLibCommand(config).run(args)

    # The real run
    FetchLibCommand(config).run(args)

    assert re.match(
        r"Library charms.operator_libs_linux.v0.snap was already up to date in version 0.[0-9]+.",
        emitter.interactions[-1].args[1],
    )


@pytest.mark.slow
def test_fetchlib_store_same_versions_different_hash(
    emitter: craft_cli.pytest_plugin.RecordingEmitter, new_path: pathlib.Path, config
):
    """The store has the lib in the same version, but with different content."""
    args = argparse.Namespace(library="charms.operator_libs_linux.v0.snap", format=None)
    lib_path = utils.get_lib_path("operator-libs-linux", "snap", 0)
    # This run is a setup run
    FetchLibCommand(config).run(args)
    with lib_path.open("a+") as f:
        f.write("# This changes the hash!")

    # The real run
    FetchLibCommand(config).run(args)

    assert emitter.interactions[-1].args[1] == (
        "Library charms.operator_libs_linux.v0.snap has local changes, cannot be updated."
    )


# endregion


def test_create_track(emitter, service_factory, config):
    cmd = CreateTrack(config)
    args = argparse.Namespace(
        name="my-charm",
        track=["my-track"],
        automatic_phasing_percentage=None,
        format="json",
    )
    mock_create_tracks = mock.Mock()
    track = publisher.Track.unmarshal(
        {
            "name": "my-track",
            "automatic-phasing-percentage": None,
            "created-at": datetime.datetime.now(),
        }
    )
    mock_get_package_metadata = mock.Mock(
        return_value=publisher.RegisteredName.unmarshal(
            {
                "id": "mentalism",
                "private": False,
                "publisher": {"id": "EliBosnick"},
                "status": "hungry",
                "store": "charmhub",
                "type": "charm",
                "tracks": [
                    track,
                    publisher.Track.unmarshal(
                        {
                            "name": "latest",
                            "automatic-phasing-percentage": None,
                            "created-at": datetime.datetime.now(),
                        }
                    ),
                ],
            }
        )
    )

    service_factory.store._publisher.create_tracks = mock_create_tracks
    service_factory.store._publisher.get_package_metadata = mock_get_package_metadata

    cmd.run(args)

    emitter.assert_json_output(
        [{"name": "my-track", "automatic-phasing-percentage": None}]
    )
