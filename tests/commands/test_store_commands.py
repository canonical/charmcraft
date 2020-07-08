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
from argparse import Namespace
from unittest.mock import patch, call, MagicMock

import pytest

from charmcraft.commands.store import (
    ListRegisteredCommand,
    LoginCommand,
    LogoutCommand,
    RegisterNameCommand,
    WhoamiCommand,
)
from charmcraft.commands.store.store import User, Charm


# used a lot!
noargs = Namespace()


@pytest.fixture
def store_mock():
    store_mock = MagicMock()
    with patch('charmcraft.commands.store.Store', lambda: store_mock):
        yield store_mock


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

    ListRegisteredCommand('group').run(noargs)

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

    ListRegisteredCommand('group').run(noargs)

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

    ListRegisteredCommand('group').run(noargs)

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

    ListRegisteredCommand('group').run(noargs)

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
