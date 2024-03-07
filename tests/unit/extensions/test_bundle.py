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
"""Unit tests for the bundle extension."""
import pathlib
import textwrap

import pytest

from charmcraft import const
from charmcraft.extensions import Bundle


@pytest.fixture()
def extension():
    return Bundle(project_root=pathlib.Path("/root/project"), yaml_data={})


@pytest.mark.parametrize(
    ("bundle_yaml", "root_snippet"),
    [
        ("{}",{"bundle": {}}),
        (
            textwrap.dedent(
                """\
                name: blah
                description: A test bundle
                series: bionic
                """
            ),
            {
                "name": "blah",
                "description": "A test bundle",
                "bundle": {
                    "name": "blah",
                    "description": "A test bundle",
                    "series": "bionic",
                }
            }
        ),
    ]
)
def test_get_root_snippet(fs, extension, bundle_yaml, root_snippet):
    fs.create_file("/root/project/bundle.yaml", contents=bundle_yaml)

    assert extension.get_root_snippet() == root_snippet


@pytest.mark.parametrize(
    "yaml_data",
    [
        {},
        {"parts": {}},
        {"parts": {"my-part": {"plugin": "nil"}}},
    ],
)
def test_get_parts_snippet_no_parts(yaml_data):
    bundle_extension = Bundle(project_root=pathlib.Path("/root/project"), yaml_data=yaml_data)

    assert bundle_extension.get_parts_snippet() == {"bundle": {"plugin": "bundle", "source": "."}}
