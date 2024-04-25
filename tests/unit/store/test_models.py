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
"""Tests for store models."""

import pytest

from charmcraft.store import models


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            {
                "charm-name": "abc",
                "library-name": "def",
                "library-id": "id",
                "api": 1,
                "patch": 123,
                "hash": "hashyhash",
            },
            models.Library(
                charm_name="abc",
                lib_name="def",
                lib_id="id",
                api=1,
                patch=123,
                content_hash="hashyhash",
                content=None,
            ),
        ),
        (
            {
                "charm-name": "abc",
                "library-name": "def",
                "library-id": "id",
                "api": 1,
                "patch": 123,
                "hash": "hashyhash",
                "content": "I am a library.",
            },
            models.Library(
                charm_name="abc",
                lib_name="def",
                lib_id="id",
                api=1,
                patch=123,
                content_hash="hashyhash",
                content="I am a library.",
            ),
        ),
    ],
)
def test_library_from_dict(data, expected):
    assert models.Library.from_dict(data) == expected
