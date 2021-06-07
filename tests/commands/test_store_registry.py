# Copyright 2021 Canonical Ltd.
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
import io
import json
import logging
from unittest.mock import patch

import pytest
import requests

from charmcraft.cmdbase import CommandError
from charmcraft.commands.store.registry import (
    ImageHandler,
    MANIFEST_LISTS,
    MANIFEST_V2_MIMETYPE,
    OCIRegistry,
    assert_response_ok,
)


# -- tests for response verifications


def create_response(status_code=200, headers=None, raw_content=b"", json_content=None):
    """Create a fake requests' response."""
    if headers is None:
        headers = {}

    if json_content is not None:
        headers.setdefault("Content-Type", "application/json")
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
    with pytest.raises(CommandError) as cm:
        assert_response_ok(response)
    assert str(cm.value) == "Response with errors from server: {}".format(errors)


def test_assert_response_bad_status_code_with_json_errors():
    """Different status code than expected, with the server including errors."""
    errors = [{"foo": "bar"}]
    test_content = {"errors": errors}
    response = create_response(status_code=404, json_content=test_content)
    with pytest.raises(CommandError) as cm:
        assert_response_ok(response)
    assert str(cm.value) == (
        "Wrong status code from server (expected=200, got=404) errors={} "
        "headers={{'Content-Type': 'application/json'}}".format(errors)
    )


def test_assert_response_bad_status_code_blind():
    """Different status code than expected, no more info."""
    response = create_response(status_code=500, raw_content=b"stuff")
    with pytest.raises(CommandError) as cm:
        assert_response_ok(response)
    assert str(cm.value) == (
        "Wrong status code from server (expected=200, got=500) errors=None headers={}"
    )


# -- tests for OCIRegistry auth & hit helpers


def test_auth_simple(responses):
    """Simple authentication."""
    responses.add(
        responses.GET,
        "https://auth.fakereg.com?service=test-service&scope=test-scope",
        json={"token": "test-token"},
    )

    ocireg = OCIRegistry("https://fakereg.com", "test-image")
    auth_info = dict(
        realm="https://auth.fakereg.com", service="test-service", scope="test-scope"
    )
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    assert sent_auth_header is None


def test_auth_with_credentials(caplog, responses):
    """Authenticate passing credentials."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

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
    auth_info = dict(
        realm="https://auth.fakereg.com", service="test-service", scope="test-scope"
    )
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    expected_encoded = base64.b64encode(b"test-user:test-password")
    assert sent_auth_header == "Basic " + expected_encoded.decode("ascii")

    # generic auth indication is logged but NOT the credentials
    expected = "Authenticating! {}".format(auth_info)
    assert [expected] == [rec.message for rec in caplog.records]


def test_auth_with_just_username(caplog, responses):
    """Authenticate passing credentials."""
    responses.add(
        responses.GET,
        "https://auth.fakereg.com?service=test-service&scope=test-scope",
        json={"token": "test-token"},
    )

    ocireg = OCIRegistry("https://fakereg.com", "test-image", username="test-user")
    auth_info = dict(
        realm="https://auth.fakereg.com", service="test-service", scope="test-scope"
    )
    token = ocireg._authenticate(auth_info)
    assert token == "test-token"
    sent_auth_header = responses.calls[0].request.headers.get("Authorization")
    expected_encoded = base64.b64encode(b"test-user:")
    assert sent_auth_header == "Basic " + expected_encoded.decode("ascii")


def test_hit_simple_initial_auth_ok(caplog, responses):
    """Simple GET with auth working at once."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

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
    assert [expected] == [rec.message for rec in caplog.records]


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
    responses.add(
        responses.GET, "https://fakereg.com/api/stuff", headers=headers, status=401
    )
    responses.add(responses.GET, "https://fakereg.com/api/stuff")

    # try it, isolating the re-authentication (tested separatedly above)
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
    responses.add(
        responses.GET, "https://fakereg.com/api/stuff", headers=headers, status=401
    )

    # try it, isolating the re-authentication (tested separatedly above)
    expected = (
        "Bad 401 response: Bearer not found; "
        "headers: {.*'Www-Authenticate': 'broken header'.*}"
    )
    with pytest.raises(CommandError, match=expected):
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
    response = ocireg._hit(
        "POST", "https://fakereg.com/api/stuff", headers={"FOO": "bar"}
    )
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


# -- tests for other OCIRegistry helpers: full url and checkers if stuff uploaded


def test_get_fully_qualified_url():
    """Check that the url is built correctly."""
    ocireg = OCIRegistry("https://fakereg.com", "test-orga/test-image")
    url = ocireg.get_fully_qualified_url("sha256:thehash")
    assert url == "fakereg.com/test-orga/test-image@sha256:thehash"


# -- tests for some OCIRegistry helpers


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


def test_ociregistry_is_item_uploaded_strange_response(responses, caplog):
    """Unexpected response."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

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
    assert expected in [rec.message for rec in caplog.records]


# -- test for the OCIRegistry manifest upload


def test_ociregistry_upload_manifest_v2(responses, caplog):
    """Upload a V2 manifest."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")
    ocireg = OCIRegistry("https://fakereg.com", "test-image")

    url = "https://fakereg.com/v2/test-image/manifests/test-reference"
    responses.add(responses.PUT, url, status=201)

    # try it
    raw_manifest_data = "test-manifest"
    ocireg.upload_manifest(raw_manifest_data, "test-reference")

    # check logs
    log_lines = [rec.message for rec in caplog.records]
    assert "Uploading manifest with reference test-reference" in log_lines
    assert "Manifest uploaded OK" in log_lines

    # check header and data sent
    assert responses.calls[0].request.headers["Content-Type"] == MANIFEST_V2_MIMETYPE
    assert responses.calls[0].request.body == raw_manifest_data.encode("ascii")


# -- tests for the OCIRegistry manifest download


def test_get_manifest_simple_v2(responses, caplog):
    """Straightforward download of a v2 manifest."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    ocireg = OCIRegistry("https://fakereg.com", "test-orga/test-image")
    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest"}
    response_content = {"schemaVersion": 2, "foo": "bar", "unicodecontent": "moño"}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )

    # try it
    sublist, digest, raw_manifest = ocireg.get_manifest("test-reference")
    assert sublist is None
    assert digest == "test-digest"
    assert raw_manifest == responses.calls[0].response.text  # must be exactly the same

    log_lines = [rec.message for rec in caplog.records]
    assert "Getting manifests list for test-reference" in log_lines
    assert "Got the manifest directly, schema 2" in log_lines

    assert responses.calls[0].request.headers["Accept"] == MANIFEST_LISTS


def test_get_manifest_v1_and_redownload(responses, caplog):
    """Get a v2 manifest after initially getting a v1."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    ocireg = OCIRegistry("https://fakereg.com", "test-orga/test-image")
    # first response with v1 manifest
    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest"}
    response_content = {"schemaVersion": 1}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )
    # second response with v2 manifest, note the changed digest!
    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest-for-real"}
    response_content = {"schemaVersion": 2}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )

    # try it
    sublist, digest, raw_manifest = ocireg.get_manifest("test-reference")
    assert sublist is None
    assert digest == "test-digest-for-real"
    assert raw_manifest == responses.calls[1].response.text  # the second one

    log_lines = [rec.message for rec in caplog.records]
    assert "Getting manifests list for test-reference" in log_lines
    assert "Got the manifest directly, schema 1" in log_lines
    assert "Got the v2 manifest ok" in log_lines

    assert responses.calls[0].request.headers["Accept"] == MANIFEST_LISTS
    assert responses.calls[1].request.headers["Accept"] == MANIFEST_V2_MIMETYPE


def test_get_manifest_simple_multiple(responses):
    """Straightforward download of a multiple manifest."""
    ocireg = OCIRegistry("https://fakereg.com", "test-orga/test-image")
    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest"}
    lot_of_manifests = [
        {"manifest1": "stuff"},
        {"manifest2": "morestuff", "foo": "bar"},
    ]
    response_content = {"manifests": lot_of_manifests}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )

    # try it
    sublist, digest, raw_manifest = ocireg.get_manifest("test-reference")
    assert sublist == lot_of_manifests
    assert digest == "test-digest"
    assert raw_manifest == responses.calls[0].response.text  # exact


def test_get_manifest_bad_v2(responses, caplog):
    """Couldn't get a v2 manifest."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")
    ocireg = OCIRegistry("https://fakereg.com", "test-orga/test-image")

    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest"}
    response_content = {"schemaVersion": 1}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )

    # second response with a bad manifest
    url = "https://fakereg.com/v2/test-orga/test-image/manifests/test-reference"
    response_headers = {"Docker-Content-Digest": "test-digest-for-real"}
    response_content = {"sadly broken": ":("}
    responses.add(
        responses.GET, url, status=200, headers=response_headers, json=response_content
    )

    # try it
    with pytest.raises(CommandError) as cm:
        ocireg.get_manifest("test-reference")
    assert str(cm.value) == "Manifest v2 not found for 'test-reference'."
    expected = (
        "Got something else when asking for a v2 manifest: {'sadly broken': ':('}"
    )
    assert expected in [rec.message for rec in caplog.records]


# -- tests for the ImageHandler 'get_destination_url' functionality


@pytest.fixture
def mocked_imagehandler():
    """Provide an ImageHandler with a mocked registry.

    This is to isolate the use of the registry from the internal behaviour.
    """
    registry = OCIRegistry("https://registry.hub.docker.com", "test-orga/test-image")
    im = ImageHandler(registry)
    with patch.object(im, "registry", autospec=True):
        yield im


def test_imagehandler_getdestinationurl_ok(mocked_imagehandler):
    """Get the destination URL ok."""
    dst_registry = mocked_imagehandler.registry
    dst_registry.is_manifest_already_uploaded.return_value = True

    manifest_info = (
        "dontcare",
        "test-digest",
        "dontcare",
    )  # (sublist, digest, raw_manifest)
    dst_registry.get_manifest.return_value = manifest_info

    dst_registry.get_fully_qualified_url.return_value = "test-final-url"

    # call and check final result
    result = mocked_imagehandler.get_destination_url("test-reference")
    assert result == "test-final-url"

    # check the registry was called properly
    dst_registry.is_manifest_already_uploaded.assert_called_with("test-reference")
    dst_registry.get_manifest.assert_called_with("test-reference")
    dst_registry.get_fully_qualified_url.assert_called_with("test-digest")


def test_imagehandler_getdestinationurl_missing(mocked_imagehandler):
    """The indicated reference does not exist in the registry."""
    mocked_imagehandler.registry.is_manifest_already_uploaded.return_value = False
    expected_error = (
        "The 'test-reference' image does not exist in the destination registry"
    )
    with pytest.raises(CommandError, match=expected_error):
        mocked_imagehandler.get_destination_url("test-reference")
