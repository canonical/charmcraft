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
import sys
from unittest import mock

import pytest

from charmcraft import env
from charmcraft.application.commands import FetchLibCommand
from charmcraft.cmdbase import JSON_FORMAT
from charmcraft.store.models import Library
from tests import factory


@pytest.fixture
def store_mock():
    """The fixture to fake the store layer in all the tests."""
    store_mock = mock.MagicMock()

    def validate_params(config, ephemeral=False, needs_auth=True):
        """Check that the store received the Charmhub configuration and ephemeral flag."""
        assert config == env.CharmhubConfig()
        assert isinstance(ephemeral, bool)
        assert isinstance(needs_auth, bool)
        return store_mock

    with mock.patch("charmcraft.application.commands.store.Store", validate_params):
        yield store_mock


# region fetch-lib tests
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_simple_downloaded(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="testcharm",
    )

    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips(
            [{"charm_name": "testcharm", "lib_name": "testlib", "api": 0}]
        ),
        mock.call.get_library("testcharm", lib_id, 0),
    ]
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "fetched": {
                    "patch": 7,
                    "content_hash": "abc",
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = "Library charms.testcharm.v0.testlib version 0.7 downloaded."
        emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "testcharm" / "v0" / "testlib.py"
    assert saved_file.read_text() == lib_content


def test_fetchlib_simple_dash_in_name(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="test-charm",
    )

    args = argparse.Namespace(library="charms.test_charm.v0.testlib", format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips(
            [{"charm_name": "test-charm", "lib_name": "testlib", "api": 0}]
        ),
        mock.call.get_library("test-charm", lib_id, 0),
    ]
    expected = "Library charms.test_charm.v0.testlib version 0.7 downloaded."
    emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "test_charm" / "v0" / "testlib.py"
    assert saved_file.read_text() == lib_content


def test_fetchlib_simple_dash_in_name_on_disk(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "test-content"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="test-charm",
    )
    factory.create_lib_filepath("test-charm", "testlib", api=0, patch=1, lib_id=lib_id)

    args = argparse.Namespace(library=None, format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips([{"lib_id": "test-example-lib-id", "api": 0}]),
        mock.call.get_library("test-charm", lib_id, 0),
    ]
    expected = "Library charms.test_charm.v0.testlib updated to version 0.7."
    emitter.assert_message(expected)


def test_fetchlib_simple_updated(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for Nth time (updating it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "testcharm", "testlib", api=0, patch=1, lib_id=lib_id
    )

    new_lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=new_lib_content,
        content_hash="abc",
        api=0,
        patch=2,
        lib_name="testlib",
        charm_name="testcharm",
    )

    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
        mock.call.get_library("testcharm", lib_id, 0),
    ]
    expected = "Library charms.testcharm.v0.testlib updated to version 0.2."
    emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "testcharm" / "v0" / "testlib.py"
    assert saved_file.read_text() == new_lib_content


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_all(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Update all the libraries found in disk."""
    monkeypatch.chdir(tmp_path)

    c1, h1 = factory.create_lib_filepath(
        "testcharm1", "testlib1", api=0, patch=1, lib_id="lib_id_1"
    )
    c2, h2 = factory.create_lib_filepath(
        "testcharm2", "testlib2", api=3, patch=5, lib_id="lib_id_2"
    )

    store_mock.get_libraries_tips.return_value = {
        ("lib_id_1", 0): Library(
            lib_id="lib_id_1",
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib1",
            charm_name="testcharm1",
        ),
        ("lib_id_2", 3): Library(
            lib_id="lib_id_2",
            content=None,
            content_hash="def",
            api=3,
            patch=14,
            lib_name="testlib2",
            charm_name="testcharm2",
        ),
    }
    _store_libs_info = [
        Library(
            lib_id="lib_id_1",
            content="new lib content 1",
            content_hash="xxx",
            api=0,
            patch=2,
            lib_name="testlib1",
            charm_name="testcharm1",
        ),
        Library(
            lib_id="lib_id_2",
            content="new lib content 2",
            content_hash="yyy",
            api=3,
            patch=14,
            lib_name="testlib2",
            charm_name="testcharm2",
        ),
    ]
    store_mock.get_library.side_effect = lambda *a: _store_libs_info.pop(0)

    args = argparse.Namespace(library=None, format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips(
            [
                {"lib_id": "lib_id_1", "api": 0},
                {"lib_id": "lib_id_2", "api": 3},
            ]
        ),
        mock.call.get_library("testcharm1", "lib_id_1", 0),
        mock.call.get_library("testcharm2", "lib_id_2", 3),
    ]
    names = [
        "charms.testcharm1.v0.testlib1",
        "charms.testcharm2.v3.testlib2",
    ]
    emitter.assert_debug("Libraries found under 'lib/charms': " + str(names))
    if formatted:
        expected = [
            {
                "charm_name": "testcharm1",
                "library_name": "testlib1",
                "library_id": "lib_id_1",
                "api": 0,
                "fetched": {
                    "patch": 2,
                    "content_hash": "xxx",
                },
            },
            {
                "charm_name": "testcharm2",
                "library_name": "testlib2",
                "library_id": "lib_id_2",
                "api": 3,
                "fetched": {
                    "patch": 14,
                    "content_hash": "yyy",
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(
            [
                "Library charms.testcharm1.v0.testlib1 updated to version 0.2.",
                "Library charms.testcharm2.v3.testlib2 updated to version 3.14.",
            ]
        )

    saved_file = tmp_path / "lib" / "charms" / "testcharm1" / "v0" / "testlib1.py"
    assert saved_file.read_text() == "new lib content 1"
    saved_file = tmp_path / "lib" / "charms" / "testcharm2" / "v3" / "testlib2.py"
    assert saved_file.read_text() == "new lib content 2"


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_not_found(emitter, store_mock, config, formatted):
    """The indicated library is not found in the store."""
    store_mock.get_libraries_tips.return_value = {}
    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    store_mock.get_libraries_tips.assert_called_once_with(
        [{"charm_name": "testcharm", "lib_name": "testlib", "api": 0}]
    ),
    error_message = "Library charms.testcharm.v0.testlib not found in Charmhub."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": None,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_is_old(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """The store has an older version that what is found locally."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=6,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    store_mock.get_libraries_tips.assert_called_once_with([{"lib_id": lib_id, "api": 0}])
    error_message = "Library charms.testcharm.v0.testlib has local changes, cannot be updated."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_same_versions_same_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store situation is the same than locally."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    _, c_hash = factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash=c_hash,
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    store_mock.get_libraries_tips.assert_called_once_with([{"lib_id": lib_id, "api": 0}])
    error_message = "Library charms.testcharm.v0.testlib was already up to date in version 0.7."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_same_versions_different_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store has the lib in the same version, but with different content."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = argparse.Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = "Library charms.testcharm.v0.testlib has local changes, cannot be updated."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


# endregion
