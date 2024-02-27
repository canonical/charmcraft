# Copyright 2023 Canonical Ltd.
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
"""Unit tests for the bundle extension."""
import pathlib

import pytest

from charmcraft import const
from charmcraft.extensions import Bundle


@pytest.fixture()
def basic_bundle_extension():
    return Bundle(project_root=pathlib.Path("/root/project"), yaml_data={})


def test_get_supported_bases():
    assert Bundle.get_supported_bases() == []


@pytest.mark.parametrize("base", [None, *const.SUPPORTED_BASES])
def test_is_experimental(base):
    assert not Bundle.is_experimental(base)


def test_get_root_snippet(basic_bundle_extension):
    assert basic_bundle_extension.get_root_snippet() == {}


def test_get_part_snippet(basic_bundle_extension):
    assert basic_bundle_extension.get_part_snippet() == {}


@pytest.mark.parametrize(
    "yaml_data",
    [
        {},
        {"parts": {}},
        {"parts": {"my-part": {"plugin": "nil"}}},
    ],
)
def test_get_parts_snippet_no_parts(basic_bundle_extension, yaml_data):
    bundle_extension = Bundle(project_root=pathlib.Path("/root/project"), yaml_data=yaml_data)

    assert bundle_extension.get_parts_snippet() == {"bundle": {"plugin": "bundle", "source": "."}}
