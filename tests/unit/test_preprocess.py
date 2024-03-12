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
"""Tests for project pre-processing functions."""
import pytest

from charmcraft import preprocess

BASIC_BUNDLE = {"type": "bundle", "parts": {"bundle": {"plugin": "bundle", "source": "."}}}


@pytest.mark.parametrize(
    ("yaml_data", "expected"),
    [
        pytest.param({}, {}, id="no-type"),
        pytest.param({"type": "bundle"}, BASIC_BUNDLE, id="empty-bundle"),
        pytest.param(BASIC_BUNDLE.copy(), BASIC_BUNDLE, id="prefilled-bundle"),
    ],
)
def test_add_default_parts_correct(yaml_data, expected):
    assert preprocess.add_default_parts(yaml_data) == expected
