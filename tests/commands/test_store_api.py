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

"""Tests for the Store API layer (code in store/store.py)."""

from unittest.mock import patch, call, MagicMock

import pytest

from charmcraft.commands.store.store import Store


@pytest.fixture
def client_mock():
    client_mock = MagicMock()
    with patch('charmcraft.commands.store.store.Client', lambda: client_mock):
        yield client_mock


def test_login(client_mock):
    store = Store()
    result = store.login()
    assert client_mock.mock_calls == [
        call.clear_credentials(),
        call.get('/v1/whoami'),
    ]
    assert result is None


def test_logout(client_mock):
    store = Store()
    result = store.logout()
    assert client_mock.mock_calls == [
        call.clear_credentials(),
    ]
    assert result is None


def test_whoami(client_mock):
    store = Store()
    auth_response = {'display-name': 'John Doe', 'username': 'jdoe', 'id': '-1'}
    client_mock.get.return_value = auth_response

    result = store.whoami()

    assert client_mock.mock_calls == [
        call.get('/v1/whoami'),
    ]
    assert result.name == 'John Doe'
    assert result.username == 'jdoe'
    assert result.userid == '-1'
