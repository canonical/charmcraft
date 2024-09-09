# Copyright 2021-2022 Canonical Ltd.
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

"""Tests for the OCI Registry related functionality (code in store/registry.py)."""

import base64
import gzip
import hashlib
import io
import json
import pathlib
import sys
import tarfile
from unittest.mock import call, patch

import pytest
import requests
from craft_cli import CraftError

from charmcraft import const
from charmcraft.store import registry
from charmcraft.store.registry import (
    CONFIG_MIMETYPE,
    LAYER_MIMETYPE,
    MANIFEST_V2_MIMETYPE,
    OCTET_STREAM_MIMETYPE,
    ImageHandler,
    LocalDockerdInterface,
    OCIRegistry,
    assert_response_ok,
)

# -- tests for response verifications


def create_response(
    status_code=200, headers=None, raw_content=b"", json_content=None, content_type=None
):
    """Create a fake requests' response."""
    if headers is None:
        headers = {}

    if json_content is not None:
        headers.setdefault("Content-Type", content_type or "application/json")
        content_bytes = json.dumps(json_content).encode("utf8")
    else:
        content_bytes = raw_content

    resp = requests.Response()
    resp.status_code = status_code
    resp.raw = io.BytesIO(content_bytes)
    resp.headers = headers  # not case insensitive, but good enough
    return resp


def test_assert_response_ok_simple_json():
    """Simple case for a good response with JSON content."""
    test_content = {"foo": 2, "bar": 1}
    response = create_response(json_content=test_content)
    result = assert_response_ok(response)
    assert result == test_content


def test_assert_response_ok_not_json():
    """A good non-json response."""
    response = create_response(raw_content=b"stuff")
    result = assert_response_ok(response)
    assert result is None


def test_assert_response_ok_different_status():
    """A good response with a different status code."""
    test_content = {"foo": 2, "bar": 1}
    response = create_response(json_content=test_content, status_code=201)
    result = assert_response_ok(response, expected_status=201)
    assert result == test_content


def test_assert_response_errors_in_result():
    """Response is as expected but server flags errors."""
    errors = [{"foo": "bar"}]
    test_content = {"errors": errors}
    response = create_response(json_content=test_content)
    with pytest.raises(CraftError) as cm:
        assert_response_ok(response)
    assert str(cm.value) == f"Response with errors from server: {errors}"


def test_assert_response_bad_status_code_with_json_errors():
    """Different status code than expected, with the server including errors."""
    errors = [{"foo": "bar"}]
    test_content = {"errors": errors}
    response = create_response(status_code=404, json_content=test_content)
    with pytest.raises(CraftError) as cm:
        assert_response_ok(response)
    error = cm.value
    assert str(error) == "Wrong status code from server (expected=200, got=404)"
    assert error.details == f"errors={errors} headers={{'Content-Type': 'application/json'}}"


def test_assert_response_bad_status_code_with_extra_json_errors():
    """The server still including errors, weird content type."""
    errors = [{"foo": "bar"}]
    test_content = {"errors": errors}
    response = create_response(
        status_code=404,
        json_content=test_content,
        content_type="application/json;stuff",
    )
    with pytest.raises(CraftError) as cm:
        assert_response_ok(response)
    error = cm.value
    assert str(error) == "Wrong status code from server (expected=200, got=404)"
    assert error.details == f"errors={errors} headers={{'Content-Type': 'application/json;stuff'}}"


def test_assert_response_bad_status_code_blind():
    """Different status code than expected, no more info."""
    response = create_response(status_code=500, raw_content=b"stuff")
    with pytest.raises(CraftError) as cm:
        assert_response_ok(response)
    error = cm.value
    assert str(error) == "Wrong status code from server (expected=200, got=500)"
    assert error.details == "errors=None headers={}"


# -- tests for OCIRegistry auth & hit helpers


def test_auth_simple(responses):
    """Simple authentication."""
    responses.add(
        responses.GET,
        "https://auth.fakereg.com?service=test-service&scope=test-scope",
        json={"token": "test-token"},
    )

    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    auth_info = {
        "realm": "https://auth.fakereg.com",
        "service": "test-service",
        "scope": "test-scope",
    }
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    assert sent_auth_header is None


def test_auth_with_credentials(emitter, responses):
    """Authenticate passing credentials."""
    responses.add(
        responses.GET,
        "https://auth.fakereg.com?service=test-service&scope=test-scope",
        json={"token": "test-token"},
    )

    ocireg = OCIRegistry(
        "https://fakereg.com",
        "test-image",
        username="test-user",
        password="test-password",
    )
    auth_info = {
        "realm": "https://auth.fakereg.com",
        "service": "test-service",
        "scope": "test-scope",
    }
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    expected_encoded = base64.b64encode(b"test-user:test-password")
    assert sent_auth_header == "Basic " + expected_encoded.decode("ascii")

    # generic auth indication is logged but NOT the credentials
    expected = f"Authenticating! {auth_info}"
    emitter.assert_trace(expected)


def test_auth_with_just_username(responses):
    """Authenticate passing credentials."""
    responses.add(
        responses.GET,
        "https://auth.fakereg.com?service=test-service&scope=test-scope",
        json={"token": "test-token"},
    )

    ocireg = OCIRegistry("https://fakereg.com", "test-image", username="test-user")
    auth_info = {
        "realm": "https://auth.fakereg.com",
        "service": "test-service",
        "scope": "test-scope",
    }
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    expected_encoded = base64.b64encode(b"test-user:")
    assert sent_auth_header == "Basic " + expected_encoded.decode("ascii")


def test_hit_simple_initial_auth_ok(emitter, responses):
    """Simple GET with auth working at once."""
    # set the Registry with an initial token
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    ocireg.auth_token = "some auth token"

    # fake a 200 response
    responses.add(responses.GET, "https://fakereg.com/api/stuff")

    # try it
    response = ocireg._hit("GET", "https://fakereg.com/api/stuff")
    assert response == responses.calls[0].response

    # verify it authed ok
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    assert sent_auth_header == "Bearer some auth token"

    # logged what it did
    expected = "Hitting the registry: GET https://fakereg.com/api/stuff"
    emitter.assert_trace(expected)


def test_hit_simple_re_auth_ok(responses):
    """Simple GET but needing to re-authenticate."""
    # set the Registry
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    ocireg.auth_token = "some auth token"

    # need to set up two responses!
    # - the 401 response with the proper info to re-auth
    # - the request that actually works
    headers = {
        "Www-Authenticate": (
            'Bearer realm="https://auth.fakereg.com/token",'
            'service="https://fakereg.com",scope="repository:library/stuff:pull"'
        )
    }
    responses.add(responses.GET, "https://fakereg.com/api/stuff", headers=headers, status=401)
    responses.add(responses.GET, "https://fakereg.com/api/stuff")

    # try it, isolating the re-authentication (tested separately above)
    with patch.object(ocireg, "_authenticate") as mock_auth:
        mock_auth.return_value = "new auth token"
        response = ocireg._hit("GET", "https://fakereg.com/api/stuff")
    assert response == responses.calls[1].response
    mock_auth.assert_called_with(
        {
            "realm": "https://auth.fakereg.com/token",
            "scope": "repository:library/stuff:pull",
            "service": "https://fakereg.com",
        }
    )

    # verify it authed ok both times, with corresponding tokens, and that it stored the new one
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    assert sent_auth_header == "Bearer some auth token"
    sent_auth_header = responses.calls[1].request.headers.get("Authorization")
    assert sent_auth_header == "Bearer new auth token"
    assert ocireg.auth_token == "new auth token"


def test_hit_simple_re_auth_problems(responses):
    """Bad response from the re-authentication process."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")

    # set only one response, a 401 which is broken and all will end there
    headers = {"Www-Authenticate": "broken header"}
    responses.add(responses.GET, "https://fakereg.com/api/stuff", headers=headers, status=401)

    # try it, isolating the re-authentication (tested separately above)
    expected = (
        "Bad 401 response: Bearer not found; headers: {.*'Www-Authenticate': 'broken header'.*}"
    )
    with pytest.raises(CraftError, match=expected):
        ocireg._hit("GET", "https://fakereg.com/api/stuff")


def test_hit_different_method(responses):
    """Simple request using something else than GET."""
    # set the Registry with an initial token
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    ocireg.auth_token = "some auth token"

    # fake a 200 response
    responses.add(responses.POST, "https://fakereg.com/api/stuff")

    # try it
    response = ocireg._hit("POST", "https://fakereg.com/api/stuff")
    assert response == responses.calls[0].response


def test_hit_including_headers(responses):
    """A request including more headers."""
    # set the Registry with an initial token
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    ocireg.auth_token = "some auth token"

    # fake a 200 response
    responses.add(responses.POST, "https://fakereg.com/api/stuff")

    # try it
    response = ocireg._hit("POST", "https://fakereg.com/api/stuff", headers={"FOO": "bar"})
    assert response == responses.calls[0].response

    # check that it sent the requested header AND the automatic auth one
    sent_headers = responses.calls[0].request.headers
    assert sent_headers.get("FOO") == "bar"
    assert sent_headers.get("Authorization") == "Bearer some auth token"


def test_hit_extra_parameters(responses):
    """The request can include extra parameters."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")

    # fake a 200 response
    responses.add(responses.PUT, "https://fakereg.com/api/stuff")

    # try it
    response = ocireg._hit("PUT", "https://fakereg.com/api/stuff", data=b"test-payload")
    assert response == responses.calls[0].response
    assert responses.calls[0].request.body == b"test-payload"


def test_hit_no_log(emitter, responses):
    """Simple request but avoiding log."""
    # set the Registry with an initial token
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    ocireg.auth_token = "some auth token"

    # fake a 200 response
    responses.add(responses.PUT, "https://fakereg.com/api/stuff")

    # try it
    ocireg._hit("PUT", "https://fakereg.com/api/stuff", log=False)

    # nothing shown!
    emitter.assert_interactions(None)


# -- tests for other OCIRegistry helpers: checkers if stuff uploaded


def test_ociregistry_is_manifest_uploaded():
    """Check the simple call with correct path to the generic verifier."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    with patch.object(ocireg, "_is_item_already_uploaded") as mock_verifier:
        mock_verifier.return_value = "whatever"
        result = ocireg.is_manifest_already_uploaded("test-reference")
    assert result == "whatever"
    url = "https://fakereg.com/v2/test-image/manifests/test-reference"
    mock_verifier.assert_called_with(url)


def test_ociregistry_is_blob_uploaded():
    """Check the simple call with correct path to the generic verifier."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    with patch.object(ocireg, "_is_item_already_uploaded") as mock_verifier:
        mock_verifier.return_value = "whatever"
        result = ocireg.is_blob_already_uploaded("test-reference")
    assert result == "whatever"
    url = "https://fakereg.com/v2/test-image/blobs/test-reference"
    mock_verifier.assert_called_with(url)


def test_ociregistry_is_item_uploaded_simple_yes(responses):
    """Simple case for the item already uploaded."""
    ocireg = OCIRegistry("http://fakereg.com/", "test-image")
    url = "http://fakereg.com/v2/test-image/stuff/some-reference"
    responses.add(responses.HEAD, url)

    # try it
    result = ocireg._is_item_already_uploaded(url)
    assert result is True


def test_ociregistry_is_item_uploaded_simple_no(responses):
    """Simple case for the item NOT already uploaded."""
    ocireg = OCIRegistry("http://fakereg.com/", "test-image")
    url = "http://fakereg.com/v2/test-image/stuff/some-reference"
    responses.add(responses.HEAD, url, status=404)

    # try it
    result = ocireg._is_item_already_uploaded(url)
    assert result is False


@pytest.mark.parametrize("redir_status", [302, 307])
def test_ociregistry_is_item_uploaded_redirect(responses, redir_status):
    """The verification is redirected to somewhere else."""
    ocireg = OCIRegistry("http://fakereg.com/", "test-image")
    url1 = "http://fakereg.com/v2/test-image/stuff/some-reference"
    url2 = "http://fakereg.com/real-check/test-image/stuff/some-reference"
    responses.add(responses.HEAD, url1, status=redir_status, headers={"Location": url2})
    responses.add(responses.HEAD, url2, status=200)

    # try it
    result = ocireg._is_item_already_uploaded(url1)
    assert result is True


def test_ociregistry_is_item_uploaded_strange_response(responses, emitter):
    """Unexpected response."""
    ocireg = OCIRegistry("http://fakereg.com/", "test-image")
    url = "http://fakereg.com/v2/test-image/stuff/some-reference"
    responses.add(responses.HEAD, url, status=400, headers={"foo": "bar"})

    # try it
    result = ocireg._is_item_already_uploaded(url)
    assert result is False
    expected = (
        "Bad response when checking for uploaded "
        "'http://fakereg.com/v2/test-image/stuff/some-reference': 400 "
        "(headers={'Content-Type': 'text/plain', 'foo': 'bar'})"
    )
    emitter.assert_debug(expected)


# -- test for the OCIRegistry manifest upload


def test_ociregistry_upload_manifest_v2(responses, emitter):
    """Upload a V2 manifest."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")

    url = "https://fakereg.com/v2/test-image/manifests/test-reference"
    responses.add(responses.PUT, url, status=201)

    # try it
    raw_manifest_data = "test-manifest"
    ocireg.upload_manifest(raw_manifest_data, "test-reference")

    # check logs
    emitter.assert_progress("Uploading manifest with reference test-reference")
    emitter.assert_progress("Manifest uploaded OK")

    # check header and data sent
    assert responses.calls[0].request.headers["Content-Type"] == MANIFEST_V2_MIMETYPE
    assert responses.calls[0].request.body == raw_manifest_data.encode("ascii")


# -- tests for the OCIRegistry blob upload


def test_ociregistry_upload_blob_complete(tmp_path, emitter, responses, monkeypatch):
    """Complete upload of a binary to the registry."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response
    pump_url_1 = base_url + "fakeurl-1"
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": pump_url_1, "Range": "0-0"},
    )

    # and the intermediate ones, chained
    pump_url_2 = base_url + "fakeurl-2"
    pump_url_3 = base_url + "fakeurl-3"
    pump_url_4 = base_url + "fakeurl-4"
    responses.add(responses.PATCH, pump_url_1, status=202, headers={"Location": pump_url_2})
    responses.add(responses.PATCH, pump_url_2, status=202, headers={"Location": pump_url_3})
    responses.add(responses.PATCH, pump_url_3, status=202, headers={"Location": pump_url_4})

    # finally, the closing url
    responses.add(
        responses.PUT,
        base_url + "fakeurl-4&digest=test-digest",
        status=201,
        headers={"Docker-Content-Digest": "test-digest"},
    )

    # prepare a fake content that will be pushed in 3 parts
    monkeypatch.setattr(registry, "CHUNK_SIZE", 3)
    bytes_source = tmp_path / "testfile"
    bytes_source.write_text("abcdefgh")

    # call!
    ocireg.upload_blob(bytes_source, 8, "test-digest")

    # check all the sent headers
    expected_headers_per_request = [
        {},  # nothing special in the initial one
        {
            "Content-Length": "3",
            "Content-Range": "0-3",
            "Content-Type": OCTET_STREAM_MIMETYPE,
        },
        {
            "Content-Length": "3",
            "Content-Range": "3-6",
            "Content-Type": OCTET_STREAM_MIMETYPE,
        },
        {
            "Content-Length": "2",
            "Content-Range": "6-8",
            "Content-Type": OCTET_STREAM_MIMETYPE,
        },
        {"Content-Length": "0", "Connection": "close"},  # closing
    ]
    for idx, expected_headers in enumerate(expected_headers_per_request):
        sent_headers = responses.calls[idx].request.headers
        for key, value in expected_headers.items():
            assert sent_headers.get(key) == value

    emitter.assert_interactions(
        [
            call("progress", "Getting URL to push the blob"),
            call(
                "trace",
                "Hitting the registry: POST https://fakereg.com/v2/test-image/blobs/uploads/",
            ),
            call("progress", "Got upload URL ok with range 0-0"),
            call("progress_bar", "Uploading...", 8),
            call("advance", 3),
            call("advance", 3),
            call("advance", 2),
            call("progress", "Closing the upload"),
            call(
                "trace",
                (
                    "Hitting the registry: PUT "
                    "https://fakereg.com/v2/test-image/fakeurl-4&digest=test-digest"
                ),
            ),
            call("progress", "Upload finished OK"),
        ]
    )


def test_ociregistry_upload_blob_bad_initial_response(responses):
    """Bad initial response when starting to upload."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response with problems
    responses.add(responses.POST, base_url + "blobs/uploads/", status=500)

    # call!
    msg = r"Wrong status code from server \(expected=202, got=500\).*"
    with pytest.raises(CraftError, match=msg):
        ocireg.upload_blob("test-filepath", 8, "test-digest")


def test_ociregistry_upload_blob_bad_upload_range(responses):
    """Received a broken range info."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response with problems
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": "test-next-url", "Range": "9-9"},
    )

    # call!
    with pytest.raises(CraftError) as cm:
        ocireg.upload_blob("test-filepath", 8, "test-digest")
    error = cm.value
    assert str(error) == "Server error: bad range received"
    assert error.details == "Range='9-9'"


def test_ociregistry_upload_blob_resumed(tmp_path, emitter, responses):
    """The upload is resumed after server indication to do so."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response, indicating that the store has already the first 5 bytes
    pump_url_1 = base_url + "fakeurl-1"
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": pump_url_1, "Range": "0-4"},
    )  # has bytes in position 0, 1, 2, 3 & 4

    # and the intermediate one
    pump_url_2 = base_url + "fakeurl-2"
    responses.add(responses.PATCH, pump_url_1, status=202, headers={"Location": pump_url_2})

    # finally, the closing url
    responses.add(
        responses.PUT,
        base_url + "fakeurl-2&digest=test-digest",
        status=201,
        headers={"Docker-Content-Digest": "test-digest"},
    )

    # prepare a fake content
    bytes_source = tmp_path / "testfile"
    bytes_source.write_text("abcdefgh")

    # call!
    ocireg.upload_blob(bytes_source, 8, "test-digest")

    # check all the sent headers
    expected_headers_per_request = [
        {},  # nothing special in the initial one
        {
            "Content-Length": "3",
            "Content-Range": "5-8",
            "Content-Type": OCTET_STREAM_MIMETYPE,
        },
        {"Content-Length": "0", "Connection": "close"},  # closing
    ]
    for idx, expected_headers in enumerate(expected_headers_per_request):
        sent_headers = responses.calls[idx].request.headers
        for key, value in expected_headers.items():
            assert sent_headers.get(key) == value

    emitter.assert_interactions(
        [
            call("progress", "Getting URL to push the blob"),
            call(
                "trace",
                "Hitting the registry: POST https://fakereg.com/v2/test-image/blobs/uploads/",
            ),
            call("progress", "Got upload URL ok with range 0-4"),
            call("progress_bar", "Uploading...", 8),
            call("advance", 5),
            call("advance", 3),
            call("progress", "Closing the upload"),
            call(
                "trace",
                (
                    "Hitting the registry: PUT "
                    "https://fakereg.com/v2/test-image/fakeurl-2&digest=test-digest"
                ),
            ),
            call("progress", "Upload finished OK"),
        ]
    )


def test_ociregistry_upload_blob_bad_response_middle(tmp_path, responses, monkeypatch):
    """Bad response from the server when pumping bytes."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response
    pump_url_1 = base_url + "fakeurl-1"
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": pump_url_1, "Range": "0-0"},
    )

    # and the intermediate ones, chained, with a crash
    pump_url_2 = base_url + "fakeurl-2"
    responses.add(responses.PATCH, pump_url_1, status=202, headers={"Location": pump_url_2})
    responses.add(responses.PATCH, pump_url_2, status=504)

    # prepare a fake content that will be pushed in 3 parts
    monkeypatch.setattr(registry, "CHUNK_SIZE", 3)
    bytes_source = tmp_path / "testfile"
    bytes_source.write_text("abcdefgh")

    # call!
    msg = r"Wrong status code from server \(expected=202, got=504\).*"
    with pytest.raises(CraftError, match=msg):
        ocireg.upload_blob(bytes_source, 8, "test-digest")


def test_ociregistry_upload_blob_bad_response_closing(tmp_path, responses):
    """Bad response from the server when closing the upload."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response
    pump_url_1 = base_url + "fakeurl-1"
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": pump_url_1, "Range": "0-0"},
    )

    # and the intermediate one
    pump_url_2 = base_url + "fakeurl-2"
    responses.add(responses.PATCH, pump_url_1, status=202, headers={"Location": pump_url_2})

    # finally, the closing url, crashing
    responses.add(responses.PUT, base_url + "fakeurl-2&digest=test-digest", status=502)

    # prepare a fake content
    bytes_source = tmp_path / "testfile"
    bytes_source.write_text("abcdefgh")

    # call!
    msg = r"Wrong status code from server \(expected=201, got=502\).*"
    with pytest.raises(CraftError, match=msg):
        ocireg.upload_blob(bytes_source, 8, "test-digest")


def test_ociregistry_upload_blob_bad_final_digest(tmp_path, responses):
    """Bad digest from server after closing the upload."""
    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    base_url = "https://fakereg.com/v2/test-image/"

    # fake the first initial response
    pump_url_1 = base_url + "fakeurl-1"
    responses.add(
        responses.POST,
        base_url + "blobs/uploads/",
        status=202,
        headers={"Location": pump_url_1, "Range": "0-0"},
    )

    # and the intermediate one
    pump_url_2 = base_url + "fakeurl-2"
    responses.add(responses.PATCH, pump_url_1, status=202, headers={"Location": pump_url_2})

    # finally, the closing url, bad digest
    responses.add(
        responses.PUT,
        base_url + "fakeurl-2&digest=test-digest",
        status=201,
        headers={"Docker-Content-Digest": "somethingelse"},
    )

    # prepare a fake content
    bytes_source = tmp_path / "testfile"
    bytes_source.write_text("abcdefgh")

    # call!
    msg = "Server error: the upload is corrupted"
    with pytest.raises(CraftError, match=msg):
        ocireg.upload_blob(bytes_source, 8, "test-digest")


# -- tests for the ImageHandler helpers and functionalities


def test_localdockerinterface_get_info_by_id_ok(responses, emitter):
    """Get image info ok."""
    test_image_info = {"some": "stuff"}
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/test-id/json",
        json=test_image_info,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_id("test-id")
    assert resp == test_image_info

    emitter.assert_interactions(None)


def test_localdockerinterface_get_info_by_id_not_found(responses, emitter):
    """Get image info for something that is not there."""
    # return 404, which means that the image was not found
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/test-id/json",
        status=404,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_id("test-id")
    assert resp is None

    emitter.assert_interactions(None)


def test_localdockerinterface_get_info_by_id_bad_response(responses, emitter):
    """Docker answered badly when checking for the image."""
    # weird dockerd behaviour
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/test-id/json",
        status=500,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_id("test-id")
    assert resp is None

    emitter.assert_debug("Bad response when validating local image: 500")


def test_localdockerinterface_get_info_by_id_disconnected(emitter, responses):
    """No daemon to talk to (see responses used as fixture but no listening)."""
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_id("test-id")
    assert resp is None

    emitter.assert_debug(
        "Cannot connect to /var/run/docker.sock , please ensure dockerd is running."
    )


def test_localdockerinterface_get_info_by_digest_ok(responses, emitter):
    """Get image info ok."""
    test_image_info_1 = {"some": "stuff", "RepoDigests": ["name @ sha256:test-digest", "other"]}
    test_image_info_2 = {"some": "stuff", "RepoDigests": ["foo", "bar"]}
    test_search_respoonse = [test_image_info_1, test_image_info_2]
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/json",
        json=test_search_respoonse,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_digest("sha256:test-digest")
    assert resp == test_image_info_1

    emitter.assert_interactions(None)


def test_localdockerinterface_get_info_by_digest_not_found(responses, emitter):
    """Get image info for something that is not there."""
    test_image_info_1 = {"some": "stuff", "RepoDigests": ["other"]}
    test_image_info_2 = {"some": "stuff", "RepoDigests": ["foo", "bar"]}
    test_search_respoonse = [test_image_info_1, test_image_info_2]
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/json",
        json=test_search_respoonse,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_digest("sha256:test-digest")
    assert resp is None

    emitter.assert_interactions(None)


def test_localdockerinterface_get_info_by_digest_none_digest(responses, emitter):
    """Get image info for something that is not there."""
    test_image_info_1 = {"some": "stuff", "RepoDigests": None}
    test_search_respoonse = [test_image_info_1]
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/json",
        json=test_search_respoonse,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_digest("sha256:test-digest")
    assert resp is None

    emitter.assert_interactions(None)


def test_localdockerinterface_get_info_by_digest_bad_response(responses, emitter):
    """Docker answered badly when checking for the image."""
    # weird dockerd behaviour
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/json",
        status=500,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_digest("sha256:test-digest")
    assert resp is None

    emitter.assert_debug("Bad response when validating local image: 500")


def test_localdockerinterface_get_info_by_digest_disconnected(emitter, responses):
    """No daemon to talk to (see responses used as fixture but no listening)."""
    ldi = LocalDockerdInterface()
    resp = ldi.get_image_info_from_digest("sha256:test-digest")
    assert resp is None

    emitter.assert_debug(
        "Cannot connect to /var/run/docker.sock , please ensure dockerd is running."
    )


def test_localdockerinterface_get_streamed_content(responses):
    """Get the content streamed."""

    class AuditableBufferedReader(io.BufferedReader):
        """BufferedReader that records the size of each reading."""

        _test_read_chunks = []

        def read(self, size):
            self._test_read_chunks.append(size)
            return super().read(size)

    test_content = AuditableBufferedReader(io.BytesIO(b"123456789"))
    responses.add(
        responses.GET,
        LocalDockerdInterface.dockerd_socket_baseurl + "/images/test-id/get",
        body=test_content,
    )
    ldi = LocalDockerdInterface()
    resp = ldi.get_streamed_image_content("test-id")
    assert test_content._test_read_chunks == []

    chunk_size = 5
    streamed = resp.iter_content(chunk_size)
    assert next(streamed) == b"12345"
    assert test_content._test_read_chunks == [chunk_size]
    assert next(streamed) == b"6789"
    assert test_content._test_read_chunks == [chunk_size, chunk_size]
    with pytest.raises(StopIteration):
        next(streamed)


class FakeRegistry:
    """A fake registry to mimic behaviour of the real one and record actions."""

    def __init__(self, image_name=None):
        self.image_name = image_name
        self.stored_manifests = {}
        self.stored_blobs = {}

    def is_manifest_already_uploaded(self, reference):
        return reference in self.stored_manifests

    def upload_manifest(self, content, reference, multiple_manifest=False):
        self.stored_manifests[reference] = (content, multiple_manifest)

    def get_manifest(self, reference):
        return self.stored_manifests[reference]

    def is_blob_already_uploaded(self, reference):
        return reference in self.stored_blobs

    def upload_blob(self, filepath, size, digest):
        self.stored_blobs[digest] = (pathlib.Path(filepath).read_bytes(), size)


class FakeDockerd:
    """A fake dockerd interface to mimic behaviour of the real one."""

    def __init__(self, image_id, image_info, image_content):
        self.image_info = image_info
        self.image_content = image_content
        self.used_id = image_id

    def get_streamed_image_content(self, image_id):
        assert image_id == self.used_id

        class FakeResponse:
            def __init__(self, content):
                self.content = io.BytesIO(content)

            def iter_content(self, chunk_size):
                while True:
                    chunk = self.content.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return FakeResponse(self.image_content)


def test_imagehandler_check_in_registry_yes():
    """Check if an image is in the registry and find it."""
    fake_registry = FakeRegistry()
    fake_registry.stored_manifests["test-reference"] = (
        None,
        "test-digest",
        "test-manifest",
    )

    im = ImageHandler(fake_registry)
    result = im.check_in_registry("test-reference")
    assert result is True


def test_imagehandler_check_in_registry_no():
    """Check if an image is in the registry and don't find it."""
    fake_registry = FakeRegistry()

    im = ImageHandler(fake_registry)
    result = im.check_in_registry("test-reference")
    assert result is False


def test_imagehandler_extract_file_simple(tmp_path, emitter):
    """Extract a file from the tarfile and gets its info."""
    # create a tar file with one file inside
    test_content = b"test content for the sample file"
    sample_file = tmp_path / "testfile.txt"
    sample_file.write_bytes(test_content)
    tar_filepath = tmp_path / "testfile.tar"
    with tarfile.open(tar_filepath, "w") as tar:
        tar.add(sample_file, "testfile.txt")

    im = ImageHandler("registry")
    with tarfile.open(tar_filepath, "r") as tar:
        tmp_filepath, size, digest = im._extract_file(tar, "testfile.txt")

    assert size == len(test_content)
    assert digest == "sha256:" + hashlib.sha256(test_content).hexdigest()
    assert pathlib.Path(tmp_filepath).read_bytes() == test_content

    emitter.assert_progress("Extracting file 'testfile.txt' from local tar (compress=False)")


def test_imagehandler_extract_file_compressed_ok(tmp_path, emitter):
    """Extract a file from the tarfile and gets its info after compressed."""
    # create a tar file with one file inside
    test_content = b"test content for the sample file"
    sample_file = tmp_path / "testfile.txt"
    sample_file.write_bytes(test_content)
    tar_filepath = tmp_path / "testfile.tar"
    with tarfile.open(tar_filepath, "w") as tar:
        tar.add(sample_file, "testfile.txt")

    im = ImageHandler("registry")
    with tarfile.open(tar_filepath, "r") as tar:
        tmp_filepath, size, digest = im._extract_file(tar, "testfile.txt", compress=True)

    compressed_content = pathlib.Path(tmp_filepath).read_bytes()
    assert size == len(compressed_content)
    assert digest == "sha256:" + hashlib.sha256(compressed_content).hexdigest()
    assert gzip.decompress(compressed_content) == test_content

    emitter.assert_progress("Extracting file 'testfile.txt' from local tar (compress=True)")


def test_imagehandler_extract_file_compressed_deterministic(tmp_path, emitter):
    """Different compressions for the same file give the exact same data."""
    # create a tar file with one file inside
    test_content = b"test content for the sample file"
    sample_file = tmp_path / "testfile.txt"
    sample_file.write_bytes(test_content)
    tar_filepath = tmp_path / "testfile.tar"
    with tarfile.open(tar_filepath, "w") as tar:
        tar.add(sample_file, "testfile.txt")

    im = ImageHandler("registry")
    with tarfile.open(tar_filepath, "r") as tar:
        _, _, digest1 = im._extract_file(tar, "testfile.txt", compress=True)
        _, _, digest2 = im._extract_file(tar, "testfile.txt", compress=True)

    assert digest1 == digest2


def test_imagehandler_uploadblob_first_time(emitter, tmp_path):
    """Upload a blob for the first time."""
    tmp_file = tmp_path / "somebinary.dat"
    tmp_file.write_text("testcontent")

    fake_registry = FakeRegistry()

    im = ImageHandler(fake_registry)
    im._upload_blob(str(tmp_file), 20, "superdigest")

    # check it was uploaded
    assert fake_registry.stored_blobs["superdigest"] == (b"testcontent", 20)

    # verify the file is cleaned
    assert not tmp_file.exists()

    emitter.assert_interactions(None)


def test_imagehandler_uploadblob_duplicated(emitter, tmp_path):
    """Upload a blob that was already there."""
    tmp_file = tmp_path / "somebinary.dat"
    tmp_file.write_text("testcontent")

    fake_registry = FakeRegistry()
    # add the entry for the blob, the value is not important
    fake_registry.stored_blobs["superdigest"] = None

    im = ImageHandler(fake_registry)
    im._upload_blob(str(tmp_file), 20, "superdigest")

    # check it was NOT uploaded again
    assert fake_registry.stored_blobs["superdigest"] is None

    # verify the file is cleaned
    assert not tmp_file.exists()

    emitter.assert_progress("Blob was already uploaded")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_imagehandler_uploadfromlocal_complete(emitter, tmp_path, responses, monkeypatch):
    """Complete process of uploading a local image."""
    # fake an image in disk (a tar file with config, layers, and a manifest)."""
    test_tar_image = tmp_path / "test-image.tar"
    test_tar_config_content = b"fake config for the image"
    test_tar_layer1_content = b"fake first layer content for the image"
    test_tar_layer2_content = b"fake second layer content for the image"
    test_manifest_content = json.dumps(
        [
            {
                "Config": const.JUJU_CONFIG_FILENAME,
                "Layers": ["layer1.bin", "layer2.bin"],
            }
        ]
    ).encode("ascii")
    tar_file = tarfile.TarFile(test_tar_image, "w")
    tar_content = [
        ("manifest.json", test_manifest_content),
        (const.JUJU_CONFIG_FILENAME, test_tar_config_content),
        ("layer1.bin", test_tar_layer1_content),
        ("layer2.bin", test_tar_layer2_content),
    ]
    for name, content in tar_content:
        ti = tarfile.TarInfo(name)
        ti.size = len(content)
        tar_file.addfile(ti, fileobj=io.BytesIO(content))
    tar_file.close()

    # prepare the image info
    image_size = test_tar_image.stat().st_size
    image_id = "test-image-id"
    image_info = {"Size": image_size, "Id": image_id, "foobar": "etc"}
    fakedockerd = FakeDockerd(image_id, image_info, test_tar_image.read_bytes())
    monkeypatch.setattr(registry, "LocalDockerdInterface", lambda: fakedockerd)

    # ensure two reads from that image, so we can properly test progress
    image_read_from_dockerd_size_1 = int(image_size * 0.7)
    image_read_from_dockerd_size_2 = image_size - image_read_from_dockerd_size_1
    monkeypatch.setattr(registry, "CHUNK_SIZE", image_read_from_dockerd_size_1)

    fake_registry = FakeRegistry()
    im = ImageHandler(fake_registry)
    main_call_result = im.upload_from_local(image_info)

    # check the uploaded blobs: first the config (as is), then the layers (compressed)
    (
        uploaded_config,
        uploaded_layer1,
        uploaded_layer2,
    ) = fake_registry.stored_blobs.items()

    (u_config_digest, (u_config_content, u_config_size)) = uploaded_config
    assert u_config_content == test_tar_config_content
    assert u_config_size == len(u_config_content)
    assert u_config_digest == "sha256:" + hashlib.sha256(u_config_content).hexdigest()

    (u_layer1_digest, (u_layer1_content, u_layer1_size)) = uploaded_layer1
    assert gzip.decompress(u_layer1_content) == test_tar_layer1_content
    assert u_layer1_size == len(u_layer1_content)
    assert u_layer1_digest == "sha256:" + hashlib.sha256(u_layer1_content).hexdigest()

    (u_layer2_digest, (u_layer2_content, u_layer2_size)) = uploaded_layer2
    assert gzip.decompress(u_layer2_content) == test_tar_layer2_content
    assert u_layer2_size == len(u_layer2_content)
    assert u_layer2_digest == "sha256:" + hashlib.sha256(u_layer2_content).hexdigest()

    # check the uploaded manifest metadata and real content
    (uploaded_manifest,) = fake_registry.stored_manifests.items()
    (u_manifest_digest, (u_manifest_content, u_manifest_multiple)) = uploaded_manifest
    assert (
        u_manifest_digest
        == "sha256:" + hashlib.sha256(u_manifest_content.encode("utf8")).hexdigest()
    )
    assert u_manifest_multiple is False

    # the response from the function we're testing is the final remote digest
    assert main_call_result == u_manifest_digest

    u_manifest = json.loads(u_manifest_content)
    assert u_manifest["mediaType"] == MANIFEST_V2_MIMETYPE
    assert u_manifest["schemaVersion"] == 2

    assert u_manifest["config"] == {
        "digest": u_config_digest,
        "mediaType": CONFIG_MIMETYPE,
        "size": u_config_size,
    }

    assert u_manifest["layers"] == [
        {
            "digest": u_layer1_digest,
            "mediaType": LAYER_MIMETYPE,
            "size": u_layer1_size,
        },
        {
            "digest": u_layer2_digest,
            "mediaType": LAYER_MIMETYPE,
            "size": u_layer2_size,
        },
    ]

    # check the output logs
    emitter.assert_interactions(
        [
            call("progress", f"Getting the image from the local repo; size={image_size}"),
            call("progress_bar", "Reading image...", image_size),
            call("advance", image_read_from_dockerd_size_1),
            call("advance", image_read_from_dockerd_size_2),
            call("progress", "Extracting file 'config.yaml' from local tar (compress=False)"),
            call(
                "progress",
                f"Uploading config blob, size={u_config_size}, digest={u_config_digest}",
            ),
            call("progress", "Extracting file 'layer1.bin' from local tar (compress=True)"),
            call(
                "progress",
                f"Uploading layer blob 1/2, size={u_layer1_size}, digest={u_layer1_digest}",
            ),
            call("progress", "Extracting file 'layer2.bin' from local tar (compress=True)"),
            call(
                "progress",
                f"Uploading layer blob 2/2, size={u_layer2_size}, digest={u_layer2_digest}",
            ),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_imagehandler_uploadfromlocal_no_config(emitter, tmp_path, monkeypatch):
    """Particular case of a manifest without config."""
    # fake an image in disk (a tar file with NO config, a layer, and a manifest)."""
    test_tar_image = tmp_path / "test-image.tar"
    test_tar_layer_content = b"fake layer content for the image"
    test_manifest_content = json.dumps(
        [
            {
                "Layers": ["layer.bin"],
            }
        ]
    ).encode("ascii")
    tar_file = tarfile.TarFile(test_tar_image, "w")
    tar_content = [
        ("manifest.json", test_manifest_content),
        ("layer.bin", test_tar_layer_content),
    ]
    for name, content in tar_content:
        ti = tarfile.TarInfo(name)
        ti.size = len(content)
        tar_file.addfile(ti, fileobj=io.BytesIO(content))
    tar_file.close()

    # return 200 with the image info
    image_size = test_tar_image.stat().st_size
    image_id = "test-image-id"
    image_info = {"Size": image_size, "Id": image_id, "foobar": "etc"}
    fakedockerd = FakeDockerd(image_id, image_info, test_tar_image.read_bytes())
    monkeypatch.setattr(registry, "LocalDockerdInterface", lambda: fakedockerd)

    fake_registry = FakeRegistry()
    im = ImageHandler(fake_registry)
    main_call_result = im.upload_from_local(image_info)

    # check the uploaded blob: just the compressed layer
    (uploaded_layer,) = fake_registry.stored_blobs.items()

    (u_layer_digest, (u_layer_content, u_layer_size)) = uploaded_layer
    assert gzip.decompress(u_layer_content) == test_tar_layer_content
    assert u_layer_size == len(u_layer_content)
    assert u_layer_digest == "sha256:" + hashlib.sha256(u_layer_content).hexdigest()

    # check the uploaded manifest metadata and real content
    (uploaded_manifest,) = fake_registry.stored_manifests.items()
    (u_manifest_digest, (u_manifest_content, u_manifest_multiple)) = uploaded_manifest
    assert (
        u_manifest_digest
        == "sha256:" + hashlib.sha256(u_manifest_content.encode("utf8")).hexdigest()
    )
    assert u_manifest_multiple is False

    # the response from the function we're testing is the final remote digest
    assert main_call_result == u_manifest_digest

    u_manifest = json.loads(u_manifest_content)
    assert u_manifest["mediaType"] == MANIFEST_V2_MIMETYPE
    assert u_manifest["schemaVersion"] == 2

    assert "config" not in u_manifest
    assert u_manifest["layers"] == [
        {
            "digest": u_layer_digest,
            "mediaType": LAYER_MIMETYPE,
            "size": u_layer_size,
        }
    ]

    # check the output logs
    emitter.assert_interactions(
        [
            call("progress", f"Getting the image from the local repo; size={image_size}"),
            call("progress_bar", "Reading image...", image_size),
            call("advance", image_size),
            call("progress", "Extracting file 'layer.bin' from local tar (compress=True)"),
            call(
                "progress",
                f"Uploading layer blob 1/1, size={u_layer_size}, digest={u_layer_digest}",
            ),
        ]
    )
