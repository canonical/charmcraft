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
"""Unit tests for store commands."""
import datetime
import textwrap

import pytest
from craft_store import models

from charmcraft.application.commands import SetResourceArchitecturesCommand
from charmcraft.utils import cli
from tests import get_fake_revision


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([], []),
        (
            [
                get_fake_revision(
                    revision=123,
                    updated_at=datetime.datetime(1900, 1, 1),
                    bases=[models.ResponseCharmResourceBase()],
                )
            ],
            [{"revision": 123, "updated_at": "1900-01-01T00:00:00", "architectures": ["all"]}],
        ),
    ],
)
def test_set_resource_architectures_output_json(emitter, updates, expected):
    SetResourceArchitecturesCommand.write_output(cli.OutputFormat.JSON, updates)

    emitter.assert_json_output(expected)


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([], "No revisions updated."),
        (
            [
                get_fake_revision(
                    revision=123,
                    updated_at=datetime.datetime(1900, 1, 1),
                    bases=[models.ResponseCharmResourceBase()],
                )
            ],
            textwrap.dedent(
                """\
                  Revision  Updated At            Architectures
                ----------  --------------------  ---------------
                       123  1900-01-01T00:00:00Z  all"""
            ),
        ),
    ],
)
def test_set_resource_architectures_output_table(emitter, updates, expected):
    SetResourceArchitecturesCommand.write_output(cli.OutputFormat.TABLE, updates)

    emitter.assert_message(expected)
