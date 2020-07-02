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

"""Tests for the Store client and authentication (code in store/client.py)."""

import json
import logging
import os
from http.cookiejar import MozillaCookieJar, Cookie
from unittest.mock import patch

import pytest
from macaroonbakery import httpbakery

from charmcraft.cmdbase import CommandError
from charmcraft.commands.store.client import Client, BASE_URL, _AuthHolder, visit_page_with_browser


# --- AuthHolder tests

@pytest.fixture
def auth_holder(tmp_path):
    """Produce an _AuthHolder instance with encapsulated resources.

    In detail:

    - writes into a temp dir

    - with a mocked webbrowser module
    """

    ah = _AuthHolder()
    ah._cookiejar_filepath = str(tmp_path / 'test.credentials')

    with patch('webbrowser.open'):
        yield ah


def get_cookie(value='test'):
    """Helper to create a cookie, which is quite long."""
    return Cookie(
        version=0, name='test-macaroon', value=value, port=None, port_specified=False,
        domain='snapcraft.io', domain_specified=True, domain_initial_dot=False, path='/',
        path_specified=True, secure=True, expires=2595425286, discard=False, comment=None,
        comment_url=None, rest=None, rfc2109=False)


def test_authholder_cookiejar_filepath():
    """Builds the cookiejar filepath in user's config directory."""
    with patch('appdirs.user_config_dir') as mock:
        mock.return_value = 'testpath'
        ah = _AuthHolder()

    assert ah._cookiejar_filepath == 'testpath'
    assert mock.called_once_with('charmcraft.credentials')


def test_authholder_clear_credentials_ok(auth_holder, caplog):
    """Clear credentials removes the file."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    with open(auth_holder._cookiejar_filepath, 'wb') as fh:
        fh.write(b'fake credentials')

    auth_holder.clear_credentials()

    assert not os.path.exists(auth_holder._cookiejar_filepath)
    expected = "Credentials cleared: file {!r} removed".format(auth_holder._cookiejar_filepath)
    assert [expected] == [rec.message for rec in caplog.records]


def test_authholder_clear_credentials_missing(auth_holder, caplog):
    """Clear credentials supports the file not being there."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    auth_holder.clear_credentials()

    assert not os.path.exists(auth_holder._cookiejar_filepath)
    expected = "Credentials file not found to be removed: {!r}".format(
        auth_holder._cookiejar_filepath)
    assert [expected] == [rec.message for rec in caplog.records]


def test_authholder_credentials_load_file_present_ok(auth_holder):
    """Credentials are properly loaded and all internal objects setup ok."""
    # create some fake cookies
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookie = get_cookie()
    fake_cookiejar.set_cookie(fake_cookie)
    fake_cookiejar.save()

    auth_holder._load_credentials()

    # check credentials
    loaded_cookies = list(auth_holder._cookiejar)
    assert len(loaded_cookies) == 1
    assert loaded_cookies[0].value == fake_cookie.value  # compare the value as no __eq__ in Cookie
    assert isinstance(auth_holder._cookiejar, MozillaCookieJar)
    assert auth_holder._old_cookies == list(auth_holder._cookiejar)

    # check other internal objects
    assert isinstance(auth_holder._client, httpbakery.Client)
    assert list(auth_holder._client.cookies)[0].value == fake_cookie.value
    (im,) = auth_holder._client._interaction_methods
    assert isinstance(im, httpbakery.WebBrowserInteractor)
    assert im._open_web_browser == visit_page_with_browser


def test_authholder_credentials_load_file_present_problem(auth_holder, caplog):
    """Support the file to be corrupt (starts blank)."""
    caplog.set_level(logging.WARNING, logger="charmcraft.commands")

    with open(auth_holder._cookiejar_filepath, 'wb') as fh:
        fh.write(b'this surely is not a valid cookie format :p')

    auth_holder._load_credentials()

    assert "Failed to read credentials" in caplog.records[0].message
    assert auth_holder._old_cookies == []


def test_authholder_credentials_load_file_missing(auth_holder, caplog):
    """Support the file to not be there (starts blank)."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    auth_holder._load_credentials()

    expected = "Credentials file not found: {!r}".format(auth_holder._cookiejar_filepath)
    assert [expected] == [rec.message for rec in caplog.records]
    assert auth_holder._old_cookies == []


def test_authholder_credentials_save_notreally(auth_holder):
    """Save does not really save if cookies didn't change."""
    # create some fake cookies
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookie = get_cookie()
    fake_cookiejar.set_cookie(fake_cookie)
    fake_cookiejar.save()

    auth_holder._load_credentials()

    with patch.object(auth_holder._cookiejar, 'save') as mock:
        auth_holder._save_credentials_if_changed()
    assert mock.call_count == 0


def test_authholder_credentials_save_reallysave(auth_holder):
    """Save really do save if cookies changed."""
    # create some fake cookies
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookie = get_cookie()
    fake_cookiejar.set_cookie(fake_cookie)
    fake_cookiejar.save()

    # make auth holder to have those credentials loaded, and also load them ourselves for
    # later comparison
    auth_holder._load_credentials()
    with open(auth_holder._cookiejar_filepath, 'rb') as fh:
        prv_file_content = fh.read()

    # set a different credential in the auth_holder (mimickin that the user authenticated
    # while doing the request)
    other_cookie = get_cookie(value='different')
    auth_holder._cookiejar.set_cookie(other_cookie)

    # call the tested method and ensure that file changed!
    auth_holder._save_credentials_if_changed()
    with open(auth_holder._cookiejar_filepath, 'rb') as fh:
        new_file_content = fh.read()
    assert new_file_content != prv_file_content

    # call the tested method again, to verify that it was calling save on the cookiejar (and
    # not that the file changed as other side effect)
    with patch.object(auth_holder._cookiejar, 'save') as mock:
        auth_holder._save_credentials_if_changed()
    assert mock.call_count == 1


def test_authholder_credentials_save_createsdir(auth_holder, tmp_path):
    """Save creates the directory if not there."""
    weird_filepath = tmp_path / 'not_created_dir' / 'deep' / 'credentials'
    auth_holder._cookiejar_filepath = str(weird_filepath)
    auth_holder._load_credentials()

    # set a cookie and ask for saving it
    auth_holder._cookiejar.set_cookie(get_cookie(value='different'))
    auth_holder._save_credentials_if_changed()

    # file should be there
    assert weird_filepath.exists()


def test_authholder_request_simple(auth_holder):
    """Load credentials the first time, hit the network, save credentials."""
    # save a cookie to be used
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookiejar.set_cookie(get_cookie())
    fake_cookiejar.save()

    other_cookie = get_cookie(value='different')

    def fake_request(self, method, url):
        # check it was properly called
        assert method == 'testmethod'
        assert url == 'testurl'

        # check credentials were loaded at this time
        assert auth_holder._cookiejar is not None

        # modify the credentials, to simulate that a re-auth happened while the request
        auth_holder._cookiejar.set_cookie(other_cookie)

        return 'raw request response'

    with patch('macaroonbakery.httpbakery.Client.request', fake_request):
        resp = auth_holder.request('testmethod', 'testurl')

    # verify response (the calling checks were done above in fake_request helper)
    assert resp == 'raw request response'

    # check the credentials were saved (that were properly loaded was also check in above's helper)
    new_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    new_cookiejar.load()
    assert list(new_cookiejar)[0].value == other_cookie.value


def test_authholder_request_credentials_already_loaded(auth_holder):
    """Do not load credentials if already there."""
    # save a cookie to be used
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookiejar.set_cookie(get_cookie())
    fake_cookiejar.save()

    # load credentials, and ensure that this will be fail if it's called again
    auth_holder._load_credentials()
    auth_holder._load_credentials = None

    with patch('macaroonbakery.httpbakery.Client.request'):
        auth_holder.request('testmethod', 'testurl')


def test_authholder_request_interaction_error(auth_holder):
    """Support authentication failure while doing the request."""
    # save a cookie to be used
    fake_cookiejar = MozillaCookieJar(auth_holder._cookiejar_filepath)
    fake_cookiejar.set_cookie(get_cookie())
    fake_cookiejar.save()

    with patch('macaroonbakery.httpbakery.Client.request') as mock:
        mock.side_effect = httpbakery.InteractionError('bad auth!!')
        expected = "Authentication failure: cannot start interactive session: bad auth!!"
        with pytest.raises(CommandError, match=expected):
            auth_holder.request('testmethod', 'testurl')


# --- Client tests

class FakeResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code

    @property
    def ok(self):
        return self.status_code == 200

    def json(self):
        return json.loads(self.content)


def test_client_get():
    """Passes the correct method."""
    with patch('charmcraft.commands.store.client._AuthHolder') as mock_auth:
        client = Client()
    client.get('/somepath')

    assert mock_auth.request.called_once_with('GET', BASE_URL + '/somepath')


def test_client_hit_success(caplog):
    """Hits the server, all ok."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    response_value = {"foo": "bar"}
    fake_response = FakeResponse(content=json.dumps(response_value), status_code=200)
    with patch('charmcraft.commands.store.client._AuthHolder') as mock_auth:
        mock_auth().request.return_value = fake_response
        client = Client()
    result = client._hit('GET', '/somepath')

    assert mock_auth.request.called_once_with('GET', BASE_URL + '/somepath')
    assert result == response_value
    expected = "Hitting the store: GET {}/somepath".format(BASE_URL)
    assert [expected] == [rec.message for rec in caplog.records]


def test_client_hit_failure():
    """Hits the server, got a failure."""
    response_value = "raw data"
    fake_response = FakeResponse(content=response_value, status_code=404)
    with patch('charmcraft.commands.store.client._AuthHolder') as mock_auth:
        mock_auth().request.return_value = fake_response
        client = Client()

    expected = r"Failure working with the Store: \[404\] 'raw data'"
    with pytest.raises(CommandError, match=expected):
        client._hit('GET', '/somepath')


def test_client_clear_credentials():
    with patch('charmcraft.commands.store.client._AuthHolder') as mock_auth:
        client = Client()
    client.clear_credentials()

    assert mock_auth.clear_credentials.called_once_with()
