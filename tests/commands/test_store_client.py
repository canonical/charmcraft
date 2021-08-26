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

import json
from unittest import mock
from unittest.mock import call, patch
import craft_store

import pytest
import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from charmcraft.cmdbase import CommandError
from charmcraft.commands.store.client import (
    Client,
    build_user_agent,
)
from charmcraft.utils import OSPlatform


# --- General tests


def test_useragent_linux(monkeypatch):
    """Construct a user-agent as a patched Linux machine"""
    monkeypatch.setenv("TRAVIS_TESTING", "1")
    os_platform = OSPlatform(system="Arch Linux", release="5.10.10-arch1-1", machine="x86_64")
    with patch("charmcraft.commands.store.client.__version__", "1.2.3"), patch(
        "charmcraft.utils.get_os_platform", return_value=os_platform
    ), patch("platform.system", return_value="Linux"), patch(
        "platform.machine", return_value="x86_64"
    ), patch(
        "platform.python_version", return_value="3.9.1"
    ):
        ua = build_user_agent()
    assert ua == "charmcraft/1.2.3 (testing) Arch Linux/5.10.10-arch1-1 (x86_64) python/3.9.1"


def test_useragent_windows(monkeypatch):
    """Construct a user-agent as a patched Windows machine"""
    monkeypatch.setenv("TRAVIS_TESTING", "1")
    with patch("charmcraft.commands.store.client.__version__", "1.2.3"), patch(
        "platform.system", return_value="Windows"
    ), patch("platform.release", return_value="10"), patch(
        "platform.machine", return_value="AMD64"
    ), patch(
        "platform.python_version", return_value="3.9.1"
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
        return json.loads(self._content)  # type: ignore

    @property
    def reason(self):
        return self._content

    @property
    def text(self):
        return self.content


@pytest.fixture
def client_class():
    """Return a client instance with craft-store's StoreClient methods mocked."""

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

    return _Client


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


def test_client_push_simple_ok(tmp_path, capsys, client_class):
    """Happy path for pushing bytes."""
    # fake some bytes to push
    test_filepath = tmp_path / "supercharm.bin"
    with test_filepath.open("wb") as fh:
        fh.write(b"abcdefgh")

    def fake_pusher(monitor):
        """Push bytes in sequence, doing verifications in the middle."""
        total_to_push = monitor.len  # not only the saved bytes, but also headers and stuff

        # one batch
        monitor.read(20)
        captured = capsys.readouterr()
        assert captured.out == "Uploading... {:.2f}%\r".format(100 * 20 / total_to_push)

        # another batch
        monitor.read(20)
        captured = capsys.readouterr()
        assert captured.out == "Uploading... {:.2f}%\r".format(100 * 40 / total_to_push)

        # check monitor is properly built
        assert isinstance(monitor.encoder, MultipartEncoder)
        filename, fh, ctype = monitor.encoder.fields["binary"]
        assert filename == "supercharm.bin"
        assert fh.name == str(test_filepath)
        assert ctype == "application/octet-stream"

        content = json.dumps(dict(successful=True, upload_id="test-upload-id"))

        return FakeResponse(content=content, status_code=200)

    client = client_class("http://api.test", "http://storage.test")
    with patch.object(client, "_storage_push", side_effect=fake_pusher):
        client.push_file(test_filepath)


def test_client_push_configured_url_simple(tmp_path, client_class):
    """The storage server can be configured."""

    def fake_pusher(monitor):
        """Check the received URL."""
        content = json.dumps(dict(successful=True, upload_id="test-upload-id"))
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
        content=json.dumps(dict(successful=False, upload_id=None)), status_code=200
    )

    client = client_class("http://api.test", "https://local.test:1234/")
    with patch.object(client, "_storage_push", return_value=fake_response):
        with pytest.raises(CommandError) as error:
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
    with patch("craft_store.HTTPClient.post") as http_post_mock:
        client._storage_push(test_monitor)

    # check request was properly called
    url = "http://test.url:0000/unscanned-upload/"
    headers = {
        "Content-Type": test_monitor.content_type,
        "Accept": "application/json",
    }
    assert http_post_mock.mock_calls == [call(url, headers=headers, data=test_monitor)]
