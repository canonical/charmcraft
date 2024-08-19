# Copyright 2024 Canonical Ltd.
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
"""Unit tests for store client."""

from unittest import mock

import pytest

from charmcraft import store


@pytest.fixture
def client() -> store.Client:
    return store.Client(api_base_url="http://charmhub.local")


@pytest.fixture
def anonymous_client() -> store.AnonymousClient:
    return store.AnonymousClient("http://charmhub.local", "http://storage.charmhub.local")


@pytest.mark.parametrize(
    ("charm", "lib_id", "api", "patch", "expected_call"),
    [
        (
            "my-charm",
            "abcdefg",
            None,
            None,
            mock.call("GET", "/v1/charm/libraries/my-charm/abcdefg", params={}),
        ),
        (
            "my-charm",
            "abcdefg",
            0,
            0,
            mock.call(
                "GET", "/v1/charm/libraries/my-charm/abcdefg", params={"api": 0, "patch": 0}
            ),
        ),
    ],
)
def test_get_library_success(
    monkeypatch, anonymous_client, charm, lib_id, api, patch, expected_call
):
    mock_get_urlpath_json = mock.Mock(
        return_value={
            "charm-name": charm,
            "library-name": "my_lib",
            "library-id": lib_id,
            "api": api or 1,
            "patch": patch or 2,
            "hash": "hashy!",
        }
    )
    monkeypatch.setattr(anonymous_client, "request_urlpath_json", mock_get_urlpath_json)

    anonymous_client.get_library(charm_name=charm, library_id=lib_id, api=api, patch=patch)

    mock_get_urlpath_json.assert_has_calls([expected_call])


@pytest.mark.parametrize(
    ("libs", "json_response", "expected"),
    [
        ([], {"libraries": []}, []),
        (
            [{"charm-name": "my-charm", "library-name": "my_lib"}],
            {
                "libraries": [
                    {
                        "charm-name": "my-charm",
                        "library-name": "my_lib",
                        "library-id": "ididid",
                        "api": 1,
                        "patch": 2,
                        "hash": "hashhashhash",
                    },
                ],
            },
            [
                store.models.Library(
                    charm_name="my-charm",
                    lib_name="my_lib",
                    lib_id="ididid",
                    api=1,
                    patch=2,
                    content=None,
                    content_hash="hashhashhash",
                ),
            ],
        ),
    ],
)
def test_fetch_libraries_metadata(monkeypatch, anonymous_client, libs, json_response, expected):
    mock_get_urlpath_json = mock.Mock(return_value=json_response)
    monkeypatch.setattr(anonymous_client, "request_urlpath_json", mock_get_urlpath_json)

    assert anonymous_client.fetch_libraries_metadata(libs) == expected

    mock_get_urlpath_json.assert_has_calls(
        [mock.call("POST", "/v1/charm/libraries/bulk", json=libs)]
    )
