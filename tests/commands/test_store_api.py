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

import logging
from unittest.mock import patch, call, MagicMock

import pytest
from dateutil import parser

from charmcraft.commands.store.store import Store, Library


@pytest.fixture
def client_mock():
    client_mock = MagicMock()
    with patch('charmcraft.commands.store.store.Client', lambda: client_mock):
        yield client_mock


# -- tests for auth


def test_login(client_mock):
    """Simple login case."""
    store = Store()
    result = store.login()
    assert client_mock.mock_calls == [
        call.clear_credentials(),
        call.get('/v1/whoami'),
    ]
    assert result is None


def test_logout(client_mock):
    """Simple logout case."""
    store = Store()
    result = store.logout()
    assert client_mock.mock_calls == [
        call.clear_credentials(),
    ]
    assert result is None


def test_whoami(client_mock):
    """Simple whoami case."""
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


# -- tests for register and list names


def test_register_name(client_mock):
    """Simple register case."""
    store = Store()
    result = store.register_name('testname')

    assert client_mock.mock_calls == [
        call.post('/v1/charm', {'name': 'testname'}),
    ]
    assert result is None


def test_list_registered_names_empty(client_mock):
    """List registered names getting an empty response."""
    store = Store()

    auth_response = {'results': []}
    client_mock.get.return_value = auth_response

    result = store.list_registered_names()

    assert client_mock.mock_calls == [
        call.get('/v1/charm')
    ]
    assert result == []


def test_list_registered_names_multiple(client_mock):
    """List registered names getting a multiple response."""
    store = Store()

    auth_response = {'results': [
        {'name': 'name1', 'private': False, 'status': 'status1'},
        {'name': 'name2', 'private': True, 'status': 'status2'},
    ]}
    client_mock.get.return_value = auth_response

    result = store.list_registered_names()

    assert client_mock.mock_calls == [
        call.get('/v1/charm')
    ]
    item1, item2 = result
    assert item1.name == 'name1'
    assert not item1.private
    assert item1.status == 'status1'
    assert item2.name == 'name2'
    assert item2.private
    assert item2.status == 'status2'


# -- tests for upload


def test_upload_straightforward(client_mock, caplog):
    """The full and successful upload case."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")
    store = Store()

    # the first response, for when pushing bytes
    test_upload_id = 'test-upload-id'
    client_mock.push.return_value = test_upload_id

    # the second response, for telling the store it was pushed
    test_status_url = 'https://store.c.c/status'
    client_mock.post.return_value = {'status-url': test_status_url}

    # the third response, status ok (note the patched UPLOAD_ENDING_STATUSES below)
    test_revision = 123
    test_status_ok = 'test-status'
    status_response = {'revisions': [{'status': test_status_ok, 'revision': test_revision}]}
    client_mock.get.return_value = status_response

    test_status_resolution = 'test-ok-or-not'
    fake_statuses = {test_status_ok: test_status_resolution}
    test_charm_name = 'test-name'
    test_filepath = 'test-filepath'
    with patch.dict('charmcraft.commands.store.store.UPLOAD_ENDING_STATUSES', fake_statuses):
        result = store.upload(test_charm_name, test_filepath)

    # check all client calls
    assert client_mock.mock_calls == [
        call.push(test_filepath),
        call.post('/v1/charm/{}/revisions'.format(test_charm_name), {'upload-id': test_upload_id}),
        call.get(test_status_url),
    ]

    # check result (build after patched ending struct)
    assert result.ok == test_status_resolution
    assert result.status == test_status_ok
    assert result.revision == test_revision

    # check logs
    expected = [
        "Upload test-upload-id started, got status url https://store.c.c/status",
        "Status checked: " + str(status_response),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_upload_polls_status(client_mock, caplog):
    """Upload polls status url until the end is indicated."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")
    store = Store()

    # first and second response, for pushing bytes and let the store know about it
    test_upload_id = 'test-upload-id'
    client_mock.push.return_value = test_upload_id
    test_status_url = 'https://store.c.c/status'
    client_mock.post.return_value = {'status-url': test_status_url}

    # the status checking response, will answer something not done yet twice, then ok
    test_revision = 123
    test_status_ok = 'test-status'
    status_response_1 = {'revisions': [{'status': 'still-scanning', 'revision': None}]}
    status_response_2 = {'revisions': [{'status': 'more-revisions', 'revision': None}]}
    status_response_3 = {'revisions': [{'status': test_status_ok, 'revision': test_revision}]}
    client_mock.get.side_effect = [status_response_1, status_response_2, status_response_3]

    test_status_resolution = 'clean and crispy'
    fake_statuses = {test_status_ok: test_status_resolution}
    with patch.dict('charmcraft.commands.store.store.UPLOAD_ENDING_STATUSES', fake_statuses):
        with patch('charmcraft.commands.store.store.POLL_DELAY', 0.01):
            result = store.upload('some-name', 'some-filepath')

    # check the status-checking client calls (kept going until third one)
    assert client_mock.mock_calls[2:] == [
        call.get(test_status_url),
        call.get(test_status_url),
        call.get(test_status_url),
    ]

    # check result which must have values from final result
    assert result.ok == test_status_resolution
    assert result.status == test_status_ok
    assert result.revision == test_revision

    # check logs
    expected = [
        "Upload test-upload-id started, got status url https://store.c.c/status",
        "Status checked: " + str(status_response_1),
        "Status checked: " + str(status_response_2),
        "Status checked: " + str(status_response_3),
    ]
    assert expected == [rec.message for rec in caplog.records]


# -- tests for list revisions


def test_list_revisions_ok(client_mock):
    """One revision ok."""
    store = Store()
    client_mock.get.return_value = {'revisions': [
        {
            'revision': 7,
            'version': 'v7',
            'created-at': '2020-06-29T22:11:00.123',
            'status': 'approved',
            'errors': None,
        }
    ]}

    result = store.list_revisions('some-name')

    assert client_mock.mock_calls == [
        call.get('/v1/charm/some-name/revisions')
    ]

    (item,) = result
    assert item.revision == 7
    assert item.version == 'v7'
    assert item.created_at == parser.parse('2020-06-29T22:11:00.123')
    assert item.status == 'approved'
    assert item.errors == []


def test_list_revisions_empty(client_mock):
    """No revisions listed."""
    store = Store()
    client_mock.get.return_value = {'revisions': []}

    result = store.list_revisions('some-name')

    assert client_mock.mock_calls == [
        call.get('/v1/charm/some-name/revisions')
    ]
    assert result == []


def test_list_revisions_errors(client_mock):
    """One revision with errors."""
    store = Store()
    client_mock.get.return_value = {'revisions': [
        {
            'revision': 7,
            'version': 'v7',
            'created-at': '2020-06-29T22:11:00.123',
            'status': 'rejected',
            'errors': [
                {'message': "error text 1", 'code': "error-code-1"},
                {'message': "error text 2", 'code': "error-code-2"},
            ],
        }
    ]}

    result = store.list_revisions('some-name')

    assert client_mock.mock_calls == [
        call.get('/v1/charm/some-name/revisions')
    ]

    (item,) = result
    error1, error2 = item.errors
    assert error1.message == "error text 1"
    assert error1.code == "error-code-1"
    assert error2.message == "error text 2"
    assert error2.code == "error-code-2"


def test_list_revisions_several_mixed(client_mock):
    """All cases mixed."""
    client_mock.get.return_value = {'revisions': [
        {
            'revision': 1,
            'version': 'v1',
            'created-at': '2020-06-29T22:11:01',
            'status': 'rejected',
            'errors': [
                {'message': "error", 'code': "code"},
            ],
        },
        {
            'revision': 2,
            'version': 'v2',
            'created-at': '2020-06-29T22:11:02',
            'status': 'approved',
            'errors': None,
        },
    ]}

    store = Store()
    result = store.list_revisions('some-name')

    (item1, item2) = result

    assert item1.revision == 1
    assert item1.version == 'v1'
    assert item1.created_at == parser.parse('2020-06-29T22:11:01')
    assert item1.status == 'rejected'
    (error,) = item1.errors
    assert error.message == "error"
    assert error.code == "code"

    assert item2.revision == 2
    assert item2.version == 'v2'
    assert item2.created_at == parser.parse('2020-06-29T22:11:02')
    assert item2.status == 'approved'
    assert item2.errors == []


# -- tests for release


def test_release_simple(client_mock):
    """Releasing a revision into one channel."""
    store = Store()
    store.release('testname', 123, ['somechannel'])

    expected_body = [{'revision': 123, 'channel': 'somechannel'}]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/testname/releases', expected_body),
    ]


def test_release_multiple(client_mock):
    """Releasing a revision into multiple channels."""
    store = Store()
    store.release('testname', 123, ['channel1', 'channel2', 'channel3'])

    expected_body = [
        {'revision': 123, 'channel': 'channel1'},
        {'revision': 123, 'channel': 'channel2'},
        {'revision': 123, 'channel': 'channel3'},
    ]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/testname/releases', expected_body),
    ]


# -- tests for status


def test_status_ok(client_mock):
    """Get all the release information."""
    client_mock.get.return_value = {
        'channel-map': [
            {
                'channel': 'latest/beta',
                'expiration-date': None,
                'platform': {'architecture': 'all', 'os': 'all', 'series': 'all'},
                'progressive': {'paused': None, 'percentage': None},
                'revision': 5,
                'when': '2020-07-16T18:45:24Z',
            }, {
                'channel': 'latest/edge/mybranch',
                'expiration-date': '2020-08-16T18:46:02Z',
                'platform': {'architecture': 'all', 'os': 'all', 'series': 'all'},
                'progressive': {'paused': None, 'percentage': None},
                'revision': 10,
                'when': '2020-07-16T18:46:02Z',
            }
        ],
        'package': {
            'channels': [
                {
                    'branch': None,
                    'fallback': None,
                    'name': 'latest/stable',
                    'risk': 'stable',
                    'track': 'latest',
                }, {
                    'branch': 'mybranch',
                    'fallback':
                    'latest/stable',
                    'name': 'latest/edge/mybranch',
                    'risk': 'edge',
                    'track': 'latest',
                },
            ]
        },
        'revisions': [
            {
                'revision': 5,
                'version': '5',
                'created-at': '2020-06-29T22:11:05',
                'status': 'approved',
                'errors': None,
            }, {
                'revision': 10,
                'version': '63a852b',
                'created-at': '2020-06-29T22:11:10',
                'status': 'approved',
                'errors': None,
            },
        ],
    }

    store = Store()
    channel_map, channels, revisions = store.list_releases('testname')

    # check how the client is used
    assert client_mock.mock_calls == [
        call.get('/v1/charm/testname/releases'),
    ]

    # check response
    cmap1, cmap2 = channel_map
    assert cmap1.revision == 5
    assert cmap1.channel == 'latest/beta'
    assert cmap1.expires_at is None
    assert cmap2.revision == 10
    assert cmap2.channel == 'latest/edge/mybranch'
    assert cmap2.expires_at == parser.parse('2020-08-16T18:46:02Z')

    channel1, channel2 = channels
    assert channel1.name == 'latest/stable'
    assert channel1.track == 'latest'
    assert channel1.risk == 'stable'
    assert channel1.branch is None
    assert channel2.name == 'latest/edge/mybranch'
    assert channel2.track == 'latest'
    assert channel2.risk == 'edge'
    assert channel2.branch == 'mybranch'

    rev1, rev2 = revisions
    assert rev1.revision == 5
    assert rev1.version == '5'
    assert rev1.created_at == parser.parse('2020-06-29T22:11:05')
    assert rev1.status == 'approved'
    assert rev1.errors == []
    assert rev2.revision == 10
    assert rev2.version == '63a852b'
    assert rev2.created_at == parser.parse('2020-06-29T22:11:10')
    assert rev2.status == 'approved'
    assert rev2.errors == []


# -- tests for library related functions


def test_create_library_id(client_mock):
    """Create a new library in the store."""
    store = Store()
    client_mock.post.return_value = {'library-id': 'test-lib-id'}

    result = store.create_library_id('test-charm-name', 'test-lib-name')

    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/test-charm-name', {'library-name': 'test-lib-name'}),
    ]
    assert result == 'test-lib-id'


def test_create_library_revision(client_mock):
    """Create a new library revision in the store."""
    test_charm_name = 'test-charm-name'
    test_lib_name = 'test-lib-name'
    test_lib_id = 'test-lib-id'
    test_api = 'test-api-version'
    test_patch = 'test-patch-version'
    test_content = 'test content with quite a lot of funny Python code :p'
    test_hash = '1234'

    store = Store()
    client_mock.post.return_value = {
        'api': test_api,
        'content': test_content,
        'hash': test_hash,
        'library-id': test_lib_id,
        'library-name': test_lib_name,
        'charm-name': test_charm_name,
        'patch': test_patch,
    }

    result_lib = store.create_library_revision(
        test_charm_name, test_lib_id, test_api, test_patch, test_content, test_hash)

    payload = {
        'api': test_api,
        'patch': test_patch,
        'content': test_content,
        'hash': test_hash,
    }
    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/test-charm-name/' + test_lib_id, payload),
    ]
    assert result_lib.api == test_api
    assert result_lib.content == test_content
    assert result_lib.content_hash == test_hash
    assert result_lib.lib_id == test_lib_id
    assert result_lib.lib_name == test_lib_name
    assert result_lib.charm_name == test_charm_name
    assert result_lib.patch == test_patch


def test_get_library(client_mock):
    """Get all the information (including content) for a library revision."""
    test_charm_name = 'test-charm-name'
    test_lib_name = 'test-lib-name'
    test_lib_id = 'test-lib-id'
    test_api = 'test-api-version'
    test_patch = 'test-patch-version'
    test_content = 'test content with quite a lot of funny Python code :p'
    test_hash = '1234'

    store = Store()
    client_mock.get.return_value = {
        'api': test_api,
        'content': test_content,
        'hash': test_hash,
        'library-id': test_lib_id,
        'library-name': test_lib_name,
        'charm-name': test_charm_name,
        'patch': test_patch,
    }

    result_lib = store.get_library(test_charm_name, test_lib_id, test_api)

    assert client_mock.mock_calls == [
        call.get('/v1/charm/libraries/test-charm-name/{}?api={}'.format(test_lib_id, test_api)),
    ]
    assert result_lib.api == test_api
    assert result_lib.content == test_content
    assert result_lib.content_hash == test_hash
    assert result_lib.lib_id == test_lib_id
    assert result_lib.lib_name == test_lib_name
    assert result_lib.charm_name == test_charm_name
    assert result_lib.patch == test_patch


def test_get_tips_simple(client_mock):
    """Get info for a lib, simple case with successful result."""
    test_charm_name = 'test-charm-name'
    test_lib_name = 'test-lib-name'
    test_lib_id = 'test-lib-id'
    test_api = 'test-api-version'
    test_patch = 'test-patch-version'
    test_content = 'test content with quite a lot of funny Python code :p'
    test_hash = '1234'

    store = Store()
    client_mock.post.return_value = {'libraries': [{
        'api': test_api,
        'content': test_content,
        'hash': test_hash,
        'library-id': test_lib_id,
        'library-name': test_lib_name,
        'charm-name': test_charm_name,
        'patch': test_patch,
    }]}

    query_info = [
        {'lib_id': test_lib_id},
    ]
    result = store.get_libraries_tips(query_info)

    payload = [
        {'library-id': test_lib_id},
    ]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/bulk', payload),
    ]
    expected = {
        (test_lib_id, test_api): Library(
            api=test_api, content=test_content, content_hash=test_hash, lib_id=test_lib_id,
            lib_name=test_lib_name, charm_name=test_charm_name, patch=test_patch),
    }
    assert result == expected


def test_get_tips_empty(client_mock):
    """Get info for a lib, with an empty response."""
    test_lib_id = 'test-lib-id'

    store = Store()
    client_mock.post.return_value = {'libraries': []}

    query_info = [
        {'lib_id': test_lib_id},
    ]
    result = store.get_libraries_tips(query_info)

    payload = [
        {'library-id': test_lib_id},
    ]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/bulk', payload),
    ]
    assert result == {}


def test_get_tips_several(client_mock):
    """Get info for multiple libs at once."""
    test_charm_name_1 = 'test-charm-name-1'
    test_lib_name_1 = 'test-lib-name-1'
    test_lib_id_1 = 'test-lib-id-1'
    test_api_1 = 'test-api-version-1'
    test_patch_1 = 'test-patch-version-1'
    test_content_1 = 'test content with quite a lot of funny Python code :p'
    test_hash_1 = '1234'

    test_charm_name_2 = 'test-charm-name-2'
    test_lib_name_2 = 'test-lib-name-2'
    test_lib_id_2 = 'test-lib-id-2'
    test_api_2 = 'test-api-version-2'
    test_patch_2 = 'test-patch-version-2'
    test_content_2 = 'more awesome Python code :)'
    test_hash_2 = '5678'

    store = Store()
    client_mock.post.return_value = {'libraries': [{
        'api': test_api_1,
        'content': test_content_1,
        'hash': test_hash_1,
        'library-id': test_lib_id_1,
        'library-name': test_lib_name_1,
        'charm-name': test_charm_name_1,
        'patch': test_patch_1,
    }, {
        'api': test_api_2,
        'content': test_content_2,
        'hash': test_hash_2,
        'library-id': test_lib_id_2,
        'library-name': test_lib_name_2,
        'charm-name': test_charm_name_2,
        'patch': test_patch_2,
    }]}

    query_info = [
        {'lib_id': test_lib_id_1},
        {'lib_id': test_lib_id_2},
    ]
    result = store.get_libraries_tips(query_info)

    payload = [
        {'library-id': test_lib_id_1},
        {'library-id': test_lib_id_2},
    ]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/bulk', payload),
    ]
    expected = {
        (test_lib_id_1, test_api_1): Library(
            api=test_api_1, content=test_content_1, content_hash=test_hash_1, lib_id=test_lib_id_1,
            lib_name=test_lib_name_1, charm_name=test_charm_name_1, patch=test_patch_1),
        (test_lib_id_2, test_api_2): Library(
            api=test_api_2, content=test_content_2, content_hash=test_hash_2, lib_id=test_lib_id_2,
            lib_name=test_lib_name_2, charm_name=test_charm_name_2, patch=test_patch_2),
    }
    assert result == expected


def test_get_tips_query_combinations(client_mock):
    """Use all the combinations to specify what's queried."""
    store = Store()
    client_mock.post.return_value = {'libraries': []}

    query_info = [
        {'lib_id': 'test-lib-id-1'},
        {'lib_id': 'test-lib-id-2', 'api': 2},
        {'charm_name': 'test-charm-name-3'},
        {'charm_name': 'test-charm-name-4', 'api': 4},
        {'charm_name': 'test-charm-name-5', 'lib_name': 'test-lib-name-5'},
        {'charm_name': 'test-charm-name-6', 'lib_name': 'test-lib-name-6', 'api': 6},
    ]
    store.get_libraries_tips(query_info)

    payload = [
        {'library-id': 'test-lib-id-1'},
        {'library-id': 'test-lib-id-2', 'api': 2},
        {'charm-name': 'test-charm-name-3'},
        {'charm-name': 'test-charm-name-4', 'api': 4},
        {'charm-name': 'test-charm-name-5', 'library-name': 'test-lib-name-5'},
        {'charm-name': 'test-charm-name-6', 'library-name': 'test-lib-name-6', 'api': 6},
    ]
    assert client_mock.mock_calls == [
        call.post('/v1/charm/libraries/bulk', payload),
    ]
