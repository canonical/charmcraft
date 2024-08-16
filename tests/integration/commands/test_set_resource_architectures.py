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
"""Integration tests for set-resource-architectures command."""
import argparse
import textwrap

import pytest
from craft_store import models

from charmcraft import application
from charmcraft.application.commands import SetResourceArchitecturesCommand
from tests import get_fake_revision


@pytest.fixture
def cmd(service_factory):
    return SetResourceArchitecturesCommand(
        config={"app": application.APP_METADATA, "services": service_factory}
    )


@pytest.mark.parametrize(
    ("args", "list_response", "expected_output"),
    [
        (
            ["my-charm", "my-resource", "--revision=1", "amd64,arm64"],
            [],
            "No revisions updated.",
        ),
        (
            ["--format=json", "my-charm", "my-resource", "--revision=1", "amd64,arm64"],
            [],
            "[]",
        ),
        (
            ["my-charm", "my-resource", "--revision=1", "amd64,arm64"],
            [
                get_fake_revision(
                    revision=1,
                    bases=[models.ResponseCharmResourceBase(architectures=["amd64", "arm64"])],
                ),
                get_fake_revision(
                    revision=2,
                    bases=[models.ResponseCharmResourceBase(architectures=["riscv64"])],
                ),
            ],
            textwrap.dedent(
                """\
                  Revision  Updated At    Architectures
                ----------  ------------  ---------------
                         1  --            amd64,arm64"""
            ),
        ),
        (
            ["my-charm", "my-resource", "--revision=1", "amd64,arm64", "--format=json"],
            [
                get_fake_revision(
                    revision=1,
                    bases=[models.ResponseCharmResourceBase(architectures=["amd64", "arm64"])],
                ),
                get_fake_revision(
                    revision=2,
                    bases=[models.ResponseCharmResourceBase(architectures=["riscv64"])],
                ),
            ],
            textwrap.dedent(
                """\
                [
                    {
                        "revision": 1,
                        "updated_at": null,
                        "architectures": [
                            "amd64",
                            "arm64"
                        ]
                    }
                ]"""
            ),
        ),
    ],
)
def test_set_resource_architectures(
    emitter, service_factory, cmd, args, list_response, expected_output
):
    """Test the happy path for set-resource-architectures command."""
    service_factory.store.client.list_resource_revisions.return_value = list_response

    parser = argparse.ArgumentParser()
    cmd.fill_parser(parser)

    parsed_args = parser.parse_args(args)

    cmd.run(parsed_args)

    emitter.assert_message(expected_output)
