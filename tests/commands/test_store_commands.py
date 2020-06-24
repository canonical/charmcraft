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

import logging
from unittest.mock import patch, call, MagicMock

import pytest

from charmcraft.commands.store import LoginCommand, LogoutCommand, WhoamiCommand


@pytest.fixture
def client_mock():
    client_mock = MagicMock()
    with patch('charmcraft.commands.store.Client', lambda: client_mock):
        yield client_mock


def test_login(caplog, client_mock):
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LoginCommand('group').run([])

    assert client_mock.mock_calls == [
        call.clear_credentials(),
        call.get('/v1/whoami'),
    ]
    assert ["Login successful"] == [rec.message for rec in caplog.records]


def test_logout(caplog, client_mock):
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    LogoutCommand('group').run([])

    assert client_mock.mock_calls == [
        call.clear_credentials(),
    ]
    assert ["Credentials cleared"] == [rec.message for rec in caplog.records]


def test_whoami(caplog, client_mock):
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    auth_response = {'display-name': 'John Doe', 'username': 'jdoe', 'id': '-1'}
    client_mock.get.return_value = auth_response
    WhoamiCommand('group').run([])

    assert client_mock.mock_calls == [
        call.get('/v1/whoami'),
    ]
    expected = [
        'name:     John Doe',
        'username: jdoe',
        'id:       -1',
    ]
    assert expected == [rec.message for rec in caplog.records]
