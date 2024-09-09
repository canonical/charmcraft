# Copyright 2020-2021 Canonical Ltd.
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

import base64
import json
from unittest import mock
from unittest.mock import call, patch

import craft_store
import pytest
import requests
from craft_cli import CraftError
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from charmcraft import const
from charmcraft.store import AnonymousClient, Client, build_user_agent
from charmcraft.utils import OSPlatform

# something well formed as tests exercise the internal machinery
ENCODED_CREDENTIALS = base64.b64encode(b"secret credentials").decode()


# --- General tests


def test_useragent_linux(monkeypatch):
    """Construct a user-agent as a patched Linux machine"""
    monkeypatch.setenv("TRAVIS_TESTING", "1")
    os_platform = OSPlatform(system="Arch Linux", release="5.10.10-arch1-1", machine="x86_64")
    with (
        patch("charmcraft.store.client.__version__", "1.2.3"),
        patch("charmcraft.utils.get_os_platform", return_value=os_platform),
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="x86_64"),
        patch("platform.python_version", return_value="3.9.1"),
    ):
        ua = build_user_agent()
    assert ua == "charmcraft/1.2.3 (testing) Arch Linux/5.10.10-arch1-1 (x86_64) python/3.9.1"


def test_useragent_windows(monkeypatch):
    """Construct a user-agent as a patched Windows machine"""
    monkeypatch.setenv("TRAVIS_TESTING", "1")
    with (
        patch("charmcraft.store.client.__version__", "1.2.3"),
        patch("platform.system", return_value="Windows"),
        patch("platform.release", return_value="10"),
        patch("platform.machine", return_value="AMD64"),
        patch("platform.python_version", return_value="3.9.1"),
    ):
        ua = build_user_agent()
    assert ua == "charmcraft/1.2.3 (testing) Windows/10 (AMD64) python/3.9.1"


# --- Client tests


class FakeResponse(requests.Response):
    def __init__(self, content, status_code):
        self._content = content
        self.status_code = status_code

    @property
    def content(self):
        return self._content

    @property
    def ok(self):
        return self.status_code == 200

    def json(self):
        try:
            return json.loads(self._content)  # type: ignore
        except json.JSONDecodeError as exc:
            # the craft-store lib expects the error from requests, as what we're
            # faking here normally is a "real response"
            raise requests.exceptions.JSONDecodeError(exc.msg, exc.doc, exc.pos)

    @property
    def reason(self):
        return self._content

    @property
    def text(self):
        return self.content


@pytest.fixture
def client_class():
    """Return a client instance with craft-store's StoreClient methods mocked."""

    auth_patch = patch("craft_store.Auth.__init__", return_value=None)
    auth_patch.start()

    class _StoreClientMock(craft_store.StoreClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.login_mock = mock.Mock()
            self.logout_mock = mock.Mock()
            self.request_mock = mock.Mock()

        def login(self, *args, **kwargs):
            self.login_mock(*args, **kwargs)

        def request(self, *args, **kwargs):
            return self.request_mock(*args, **kwargs)

        def logout(self, *args, **kwargs):
            self.logout_mock(*args, **kwargs)

    class _Client(Client, _StoreClientMock):
        pass

    yield _Client

    auth_patch.stop()


def test_client_init():
    """Check how craft-store's Client is initiated."""
    api_url = "http://api.test"
    storage_url = "http://storage.test"
    user_agent = "Super User Agent"
    with patch("craft_store.StoreClient.__init__") as mock_client_init:
        with patch("charmcraft.store.client.build_user_agent") as mock_ua:
            mock_ua.return_value = user_agent
            Client(api_url, storage_url, user_agent=user_agent)
    mock_client_init.assert_called_with(
        base_url=api_url,
        storage_base_url=storage_url,
        endpoints=craft_store.endpoints.CHARMHUB,
        application_name="charmcraft",
        user_agent=user_agent,
        environment_auth=const.ALTERNATE_AUTH_ENV_VAR,
        ephemeral=False,
    )


def test_client_request_success_simple(client_class):
    """Hits the server, all ok."""
    response_value = {"foo": "bar"}
    fake_response = FakeResponse(content=json.dumps(response_value), status_code=200)
    client = client_class("http://api.test", "http://storage.test")
    client.request_mock.return_value = fake_response

    result = client.request_urlpath_json("GET", "/somepath")

    assert client.request_mock.mock_calls == [call("GET", "http://api.test/somepath")]
    assert result == response_value


def test_client_request_success_without_json_parsing(client_class):
    """Hits the server, all ok, return the raw response without parsing the json."""
    response_value = "whatever test response"
    fake_response = FakeResponse(content=response_value, status_code=200)
    client = client_class("http://api.test", "http://storage.test")
    client.request_mock.return_value = fake_response

    result = client.request_urlpath_text("GET", "/somepath")

    assert client.request_mock.mock_calls == [call("GET", "http://api.test/somepath")]
    assert result == response_value


def test_client_request_text_error(client_class):
    """Hits the server in text mode, getting an error."""
    client = client_class("http://api.test", "http://storage.test")
    original_error_text = "bad bad server"
    client.request_mock.side_effect = craft_store.errors.CraftStoreError(original_error_text)

    with pytest.raises(craft_store.errors.CraftStoreError) as cm:
        client.request_urlpath_text("GET", "/somepath")
    assert str(cm.value) == original_error_text


def test_client_request_json_error(client_class):
    """Hits the server in json mode, getting an error."""
    client = client_class("http://api.test", "http://storage.test")
    original_error_text = "bad bad server"
    client.request_mock.side_effect = craft_store.errors.CraftStoreError(original_error_text)

    with pytest.raises(craft_store.errors.CraftStoreError) as cm:
        client.request_urlpath_json("GET", "/somepath")
    assert str(cm.value) == original_error_text


def test_client_hit_success_withbody(client_class):
    """Hits the server including a body, all ok."""
    response_value = {"foo": "bar"}
    fake_response = FakeResponse(content=response_value, status_code=200)
    client = client_class("http://api.test", "http://storage.test")
    client.request_mock.return_value = fake_response

    result = client.request_urlpath_text("GET", "/somepath", "somebody")

    assert client.request_mock.mock_calls == [call("GET", "http://api.test/somepath", "somebody")]
    assert result == response_value


def test_client_init_removes_trailing_slashes(client_class):
    """The configured api url is ok even with an extra slash."""
    client = client_class("https://local.test:1234/", "http://storage.test/")

    assert client.api_base_url == "https://local.test:1234"
    assert client.storage_base_url == "http://storage.test"


def test_client_push_simple_ok(tmp_path, emitter, client_class):
    """Happy path for pushing bytes."""
    # fake some bytes to push
    test_filepath = tmp_path / "supercharm.bin"
    with test_filepath.open("wb") as fh:
        fh.write(b"abcdefgh")

    # used to store sizes from the monitor so we can assert emitter outside the fake
    # pusher after all is finished
    monitor_sizes_info = []

    def fake_pusher(monitor):
        """Push bytes in sequence, doing verifications in the middle."""
        # store the total monitor len (which is not only the saved bytes, but also
        # headers and stuff) and the prepared read batch size
        total_to_push = monitor.len
        read_size = int(total_to_push * 0.3)
        monitor_sizes_info.extend((total_to_push, read_size))

        # read twice the prepared chunk, and the rest
        monitor.read(read_size)
        monitor.read(read_size)
        monitor.read(total_to_push - read_size * 2)

        # check monitor is properly built
        assert isinstance(monitor.encoder, MultipartEncoder)
        filename, fh, ctype = monitor.encoder.fields["binary"]
        assert filename == "supercharm.bin"
        assert fh.name == str(test_filepath)
        assert ctype == "application/octet-stream"

        content = json.dumps({"successful": True, "upload_id": "test-upload-id"})

        return FakeResponse(content=content, status_code=200)

    client = client_class("http://api.test", "http://storage.test")
    with patch.object(client, "_storage_push", side_effect=fake_pusher):
        client.push_file(test_filepath)

    total_to_push, read_size = monitor_sizes_info
    emitter.assert_interactions(
        [
            call("progress", f"Starting to push {str(test_filepath)!r}"),
            call("progress_bar", "Uploading...", total_to_push, delta=False),
            call("advance", read_size),
            call("advance", read_size * 2),
            call("advance", total_to_push),
            call("progress", "Uploading bytes ended, id test-upload-id"),
        ]
    )


def test_client_push_configured_url_simple(tmp_path, client_class):
    """The storage server can be configured."""

    def fake_pusher(monitor):
        """Check the received URL."""
        content = json.dumps({"successful": True, "upload_id": "test-upload-id"})
        return FakeResponse(content=content, status_code=200)

    test_filepath = tmp_path / "supercharm.bin"
    test_filepath.write_text("abcdefgh")

    client = client_class("http://api.test", "https://local.test:1234/")
    with patch.object(client, "_storage_push", side_effect=fake_pusher):
        client.push_file(test_filepath)


def test_client_push_response_unsuccessful(tmp_path, client_class):
    """Didn't get a 200 from the Storage."""
    # fake some bytes to push
    test_filepath = tmp_path / "supercharm.bin"
    with test_filepath.open("wb") as fh:
        fh.write(b"abcdefgh")
    fake_response = FakeResponse(
        content=json.dumps({"successful": False, "upload_id": None}), status_code=200
    )

    client = client_class("http://api.test", "https://local.test:1234/")
    with patch.object(client, "_storage_push", return_value=fake_response):
        with pytest.raises(CraftError) as error:
            client.push_file(test_filepath)
            expected_error = (
                "Server error while pushing file: {'successful': False, 'upload_id': None}"
            )
            assert str(error.value) == expected_error


def test_storage_push_succesful(client_class):
    """Bytes are properly pushed to the Storage."""
    test_monitor = MultipartEncoderMonitor(
        MultipartEncoder(fields={"binary": ("filename", "somefile", "application/octet-stream")})
    )

    client = client_class("http://api.test", "http://test.url:0000")
    client._storage_push(test_monitor)

    # check request was properly called
    url = "http://test.url:0000/unscanned-upload/"
    headers = {
        "Content-Type": test_monitor.content_type,
        "Accept": "application/json",
    }
    assert client.request_mock.mock_calls == [
        call("POST", url, headers=headers, data=test_monitor)
    ]


def test_alternate_auth_login_forbidden(client_class, monkeypatch):
    """Login functionality cannot be used if alternate auth is present."""
    monkeypatch.setenv(const.ALTERNATE_AUTH_ENV_VAR, ENCODED_CREDENTIALS)
    client = client_class("http://api.test", "http://storage.test")
    with pytest.raises(CraftError) as cm:
        client.login()
    expected_error = (
        "Cannot login when using alternative auth through CHARMCRAFT_AUTH environment variable."
    )
    assert str(cm.value) == expected_error


def test_alternate_auth_logout_forbidden(client_class, monkeypatch):
    """Logout functionality cannot be used if alternate auth is present."""
    monkeypatch.setenv(const.ALTERNATE_AUTH_ENV_VAR, ENCODED_CREDENTIALS)
    client = client_class("http://api.test", "http://storage.test")
    with pytest.raises(CraftError) as cm:
        client.logout()
    expected_error = (
        "Cannot logout when using alternative auth through CHARMCRAFT_AUTH environment variable."
    )
    assert str(cm.value) == expected_error


def test_anonymous_client_init():
    """Check how craft-store's HTTPClient is initiated."""
    api_url = "http://api.test"
    storage_url = "http://storage.test"
    user_agent = "Super User Agent"
    with patch("craft_store.http_client.HTTPClient.__init__") as mock_client_init:
        with patch("charmcraft.store.client.build_user_agent") as mock_ua:
            mock_ua.return_value = user_agent
            mock_client_init.return_value = None
            AnonymousClient(api_url, storage_url)

    mock_client_init.assert_called_with(
        user_agent=user_agent,
    )


def test_anonymous_client_request_success_simple():
    """Hits the server, all ok."""
    response_value = {"foo": "bar"}
    fake_response = FakeResponse(content=json.dumps(response_value), status_code=200)
    with patch("craft_store.http_client.HTTPClient.request") as mock_http_client_request:
        mock_http_client_request.return_value = fake_response
        client = AnonymousClient("http://api.test", "http://storage.test")
        result = client.request_urlpath_json("GET", "/somepath")

    assert mock_http_client_request.mock_calls == [call("GET", "http://api.test/somepath")]
    assert result == response_value


def test_anonymous_client_request_success_without_json_parsing():
    """Hits the server, all ok, return the raw response without parsing the json."""
    response_value = "whatever test response"
    fake_response = FakeResponse(content=response_value, status_code=200)
    with patch("craft_store.http_client.HTTPClient.request") as mock_http_client_request:
        client = AnonymousClient("http://api.test", "http://storage.test")
        mock_http_client_request.return_value = fake_response
        result = client.request_urlpath_text("GET", "/somepath")

    assert mock_http_client_request.mock_calls == [call("GET", "http://api.test/somepath")]
    assert result == response_value


def test_anonymous_client_request_text_error():
    """Hits the server in text mode, getting an error."""
    with patch("craft_store.http_client.HTTPClient.request") as mock_http_client_request:
        original_error_text = "bad bad server"
        mock_http_client_request.side_effect = craft_store.errors.CraftStoreError(
            original_error_text
        )
        client = AnonymousClient("http://api.test", "http://storage.test")

        with pytest.raises(craft_store.errors.CraftStoreError) as cm:
            client.request_urlpath_text("GET", "/somepath")

    assert str(cm.value) == original_error_text


def test_anonymous_client_request_json_error():
    """Hits the server in json mode, getting an error."""
    with patch("craft_store.http_client.HTTPClient.request") as mock_http_client_request:
        original_error_text = "bad bad server"
        mock_http_client_request.side_effect = craft_store.errors.CraftStoreError(
            original_error_text
        )
        client = AnonymousClient("http://api.test", "http://storage.test")

        with pytest.raises(craft_store.errors.CraftStoreError) as cm:
            client.request_urlpath_json("GET", "/somepath")

    assert str(cm.value) == original_error_text


def test_anonymous_client_hit_success_withbody():
    """Hits the server including a body, all ok."""
    response_value = {"foo": "bar"}
    fake_response = FakeResponse(content=response_value, status_code=200)
    with patch("craft_store.http_client.HTTPClient.request") as mock_http_client_request:
        mock_http_client_request.return_value = fake_response
        client = AnonymousClient("http://api.test", "http://storage.test")

        result = client.request_urlpath_text("GET", "/somepath", "somebody")

    assert mock_http_client_request.mock_calls == [
        call("GET", "http://api.test/somepath", "somebody")
    ]
    assert result == response_value


def test_anonymous_client_init_removes_trailing_slashes():
    """The configured api url is ok even with an extra slash."""
    client = AnonymousClient("https://local.test:1234/", "http://storage.test/")

    assert client.api_base_url == "https://local.test:1234"
    assert client.storage_base_url == "http://storage.test"
