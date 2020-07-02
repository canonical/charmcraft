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
    LoginCommand,
    LogoutCommand,
    WhoamiCommand,
)
from charmcraft.commands.store.store import User


# used a lot!
noargs = Namespace()


@pytest.fixture
def store_mock():
    store_mock = MagicMock()
    with patch('charmcraft.commands.store.Store', lambda: store_mock):
        yield store_mock


def test_login(caplog, store_mock):
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LoginCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.login(),
    ]
    assert ["Login successful"] == [rec.message for rec in caplog.records]


def test_logout(caplog, store_mock):
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LogoutCommand('group').run(noargs)

    assert store_mock.mock_calls == [
        call.logout(),
    ]
    assert ["Credentials cleared"] == [rec.message for rec in caplog.records]


def test_whoami(caplog, store_mock):
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
