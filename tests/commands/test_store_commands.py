# Copyright 2020 Canonical Ltd.
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

"""Tests for the Store commands (code in store/__init__.py)."""

import logging
import os
import pathlib
from argparse import Namespace
from unittest.mock import patch, call, MagicMock

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands.store import (
    ListNamesCommand,
    LoginCommand,
    LogoutCommand,
    RegisterNameCommand,
    UploadCommand,
    WhoamiCommand,
    get_name_from_metadata,
)
from charmcraft.commands.store.store import User, Charm, Uploaded

# used a lot!
noargs = Namespace()


@pytest.fixture
def store_mock():
    """The fixture to fake the store layer in all the tests."""
    store_mock = MagicMock()
    with patch('charmcraft.commands.store.Store', lambda: store_mock):
        yield store_mock


# -- tests for helpers


def test_get_name_from_metadata_ok(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a valid metadata
    metadata_file = tmp_path / 'metadata.yaml'
    with metadata_file.open('wb') as fh:
        fh.write(b"name: test-name")

    result = get_name_from_metadata()
    assert result == "test-name"


def test_get_name_from_metadata_no_file(tmp_path, monkeypatch):
    """No metadata file to get info."""
    monkeypatch.chdir(tmp_path)
    result = get_name_from_metadata()
    assert result is None


def test_get_name_from_metadata_bad_content_garbage(tmp_path, monkeypatch):
    """The metadata file is broken."""
    monkeypatch.chdir(tmp_path)

    # put a broken metadata
    metadata_file = tmp_path / 'metadata.yaml'
    with metadata_file.open('wb') as fh:
        fh.write(b"\b00\bff -- not a realy yaml stuff")

    result = get_name_from_metadata()
    assert result is None


def test_get_name_from_metadata_bad_content_no_name(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a broken metadata
    metadata_file = tmp_path / 'metadata.yaml'
    with metadata_file.open('wb') as fh:
        fh.write(b"{}")

    result = get_name_from_metadata()
    assert result is None


# -- tests for auth commands


def test_login(caplog, store_mock):
    """Simple login case."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LoginCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.login(),
    ]
    assert ["Login successful"] == [rec.message for rec in caplog.records]


def test_logout(caplog, store_mock):
    """Simple logout case."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LogoutCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.logout(),
    ]
    assert ["Credentials cleared"] == [rec.message for rec in caplog.records]


def test_whoami(caplog, store_mock):
    """Simple whoami case."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = User(name='John Doe', username='jdoe', userid='-1')
    store_mock.whoami.return_value = store_response

    WhoamiCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    expected = [
        'name:      John Doe',
        'username:  jdoe',
        'id:        -1',
    ]
    assert expected == [rec.message for rec in caplog.records]


# -- tests for name-related commands


def test_register_name(caplog, store_mock):
    """Simple register_name case."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    args = Namespace(name='testname')
    RegisterNameCommand('group').run(args)

    assert store_mock.mock_calls == [
        call.register_name('testname'),
    ]
    expected = "Congrats! You are now the publisher of 'testname'"
    assert [expected] == [rec.message for rec in caplog.records]


def test_list_registered_empty(caplog, store_mock):
    """List registered with empty response."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = []
    store_mock.list_registered_names.return_value = store_response

    ListNamesCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.list_registered_names(),
    ]
    expected = "Nothing found"
    assert [expected] == [rec.message for rec in caplog.records]


def test_list_registered_one_private(caplog, store_mock):
    """List registered with one private item in the response."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = [
        Charm(name='charm', private=True, status='status'),
    ]
    store_mock.list_registered_names.return_value = store_response

    ListNamesCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.list_registered_names(),
    ]
    expected = [
        "Name    Visibility    Status",
        "charm   private       status",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_list_registered_one_public(caplog, store_mock):
    """List registered with one public item in the response."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = [
        Charm(name='charm', private=False, status='status'),
    ]
    store_mock.list_registered_names.return_value = store_response

    ListNamesCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.list_registered_names(),
    ]
    expected = [
        "Name    Visibility    Status",
        "charm   public        status",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_list_registered_several(caplog, store_mock):
    """List registered with several itemsssssssss in the response."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = [
        Charm(name='charm1', private=True, status='simple status'),
        Charm(name='charm2-long-name', private=False, status='other'),
        Charm(name='charm3', private=True, status='super long status'),
    ]
    store_mock.list_registered_names.return_value = store_response

    ListNamesCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.list_registered_names(),
    ]
    expected = [
        "Name              Visibility    Status",
        "charm1            private       simple status",
        "charm2-long-name  public        other",
        "charm3            private       super long status",
    ]
    assert expected == [rec.message for rec in caplog.records]


# -- tests for upload command


def test_upload_call_ok(caplog, store_mock):
    """Simple upload, success result."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = Uploaded(ok=True, status=200, revision=7)
    store_mock.upload.return_value = store_response

    args = Namespace(charm_file='whatever-cmd-arg')
    with patch('charmcraft.commands.store.UploadCommand._discover_charm') as mock_discover:
        mock_discover.return_value = ('discovered-name', 'discovered-path')
        UploadCommand('group').run(args)

    # check it called self discover helper with correct args
    mock_discover.assert_called_once_with('whatever-cmd-arg')

    assert store_mock.mock_calls == [
        call.upload('discovered-name', 'discovered-path')
    ]
    expected = "Revision 7 of 'discovered-name' created"
    assert [expected] == [rec.message for rec in caplog.records]


def test_upload_call_error(caplog, store_mock):
    """Simple upload but with a response indicating an error."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    store_response = Uploaded(ok=False, status=400, revision=None)
    store_mock.upload.return_value = store_response

    args = Namespace(charm_file='whatever-cmd-arg')
    with patch('charmcraft.commands.store.UploadCommand._discover_charm') as mock_discover:
        mock_discover.return_value = ('discovered-name', 'discovered-path')
        UploadCommand('group').run(args)

    expected = "Upload failed: got status 400"
    assert [expected] == [rec.message for rec in caplog.records]


def test_upload_discover_pathgiven_ok(tmp_path):
    """Discover charm name/path, indicated path ok."""
    charm_file = tmp_path / 'testfile.charm'
    charm_file.touch()

    name, path = UploadCommand('group')._discover_charm(charm_file)
    assert name == 'testfile'
    assert path == charm_file


def test_upload_discover_pathgiven_home_expanded(tmp_path):
    """Discover charm name/path, home-expand the indicated path."""
    fake_home = tmp_path / 'homedir'
    fake_home.mkdir()
    charm_file = fake_home / 'testfile.charm'
    charm_file.touch()

    with patch.dict(os.environ, {'HOME': str(fake_home)}):
        name, path = UploadCommand('group')._discover_charm(pathlib.Path('~/testfile.charm'))
    assert name == 'testfile'
    assert path == pathlib.Path(str(charm_file))


def test_upload_discover_pathgiven_missing(tmp_path):
    """Discover charm name/path, the indicated path is not there."""
    with pytest.raises(CommandError) as cm:
        UploadCommand('group')._discover_charm(pathlib.Path('not_really_there.charm'))
    assert str(cm.value) == "Can't access the indicated charm file: 'not_really_there.charm'"


def test_upload_discover_pathgiven_not_a_file(tmp_path):
    """Discover charm name/path, the indicated path is not a file."""
    with pytest.raises(CommandError) as cm:
        UploadCommand('group')._discover_charm(tmp_path)
    assert str(cm.value) == "The indicated charm is not a file: {!r}".format(str(tmp_path))


def test_upload_discover_default_ok(tmp_path, monkeypatch):
    """Discover charm name/path, default to get info from metadata, ok."""
    monkeypatch.chdir(tmp_path)

    # touch the charm file
    charm_file = tmp_path / 'testcharm.charm'
    charm_file.touch()

    # fake the metadata to point to that file
    with patch('charmcraft.commands.store.get_name_from_metadata') as mock:
        mock.return_value = 'testcharm'

        name, path = UploadCommand('group')._discover_charm(None)

    assert name == 'testcharm'
    assert path == pathlib.Path(str(charm_file))


def test_upload_discover_default_no_metadata(tmp_path):
    """Discover charm name/path, no metadata file to get info."""
    with patch('charmcraft.commands.store.get_name_from_metadata') as mock:
        mock.return_value = None

        with pytest.raises(CommandError) as cm:
            UploadCommand('group')._discover_charm(None)

    assert str(cm.value) == (
        "Can't access name in 'metadata.yaml' file. The 'upload' command needs to be executed in "
        "a valid project's directory, or point to a charm file with the --charm-file option.")


def test_upload_discover_default_no_charm_file(tmp_path, monkeypatch):
    """Discover charm name/path, the metadata indicates a not accesible."""
    monkeypatch.chdir(tmp_path)

    # fake the metadata to point to a missing file
    metadata_data = {'name': 'testcharm'}
    metadata_file = tmp_path / 'metadata.yaml'
    metadata_raw = yaml.dump(metadata_data).encode('ascii')
    with metadata_file.open('wb') as fh:
        fh.write(metadata_raw)

    with pytest.raises(CommandError) as cm:
        UploadCommand('group')._discover_charm(None)
    assert str(cm.value) == (
        "Can't access charm file {!r}. You can indicate a charm file with "
        "the --charm-file option.".format(str(tmp_path / 'testcharm.charm')))
