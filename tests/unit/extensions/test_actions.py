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
"""Tests for the actions.yaml extension."""
import pathlib
import textwrap

import pytest

from charmcraft import extensions


@pytest.fixture()
def extension():
    return extensions.Actions(
        project_root=pathlib.Path("/root/project"), yaml_data={"type": "charm"}
    )


@pytest.mark.parametrize(
    ("actions_yaml", "root_snippet"),
    [
        ("{}", {"actions": {}}),
        (
            textwrap.dedent(
                """\
                pause:
                  description: Pause the database.
                  additionalProperties: false
                snapshot:
                  description: |
                    Take a snapshot of the database.
                  params:
                    outfile:
                      type: string
                      description: The filename to write to.
                  additionalProperties: false
                """
            ),
            {
                "actions": {
                    "pause": {"description": "Pause the database.", "additionalProperties": False},
                    "snapshot": {
                        "description": "Take a snapshot of the database.\n",
                        "params": {
                            "outfile": {
                                "type": "string",
                                "description": "The filename to write to.",
                            }
                        },
                        "additionalProperties": False,
                    },
                }
            },
        ),
    ],
)
def test_get_root_snippet_successful_load(fs, extension, actions_yaml, root_snippet):
    fs.create_file("/root/project/actions.yaml", contents=actions_yaml)

    assert extension.get_root_snippet() == root_snippet
