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
"""Tests for metadata models."""
import json

import pytest

from charmcraft.models import metadata, project

BASIC_CHARM_METADATA_DICT = {
    "name": "test-charm",
    "summary": "A charm for testing, with a summary string that is more than seventy-eight characters long.",
    "description": "A fake charm used for testing purposes.",
}
BASIC_CHARM_DICT = {
    **BASIC_CHARM_METADATA_DICT,
    "type": "charm",
    "bases": [{"name": "ubuntu", "channel": "22.04", "architectures": ["riscv64"]}],
}

BASIC_BUNDLE_METADATA_DICT = {
    "name": "test-bundle",
    "description": "A fake bundle for testing purposes.",
}
BASIC_BUNDLE_DICT = {
    "type": "bundle",
    **BASIC_BUNDLE_METADATA_DICT,
}


@pytest.mark.parametrize(
    ("charm_dict", "expected"),
    [
        (BASIC_CHARM_DICT, BASIC_CHARM_METADATA_DICT),
        (
            dict(**BASIC_CHARM_DICT, links={"documentation": "https://docs.url/"}),
            {**BASIC_CHARM_METADATA_DICT, "docs": "https://docs.url/"},
        ),
        (
            dict(**BASIC_CHARM_DICT, links={"contact": "someone@company.com"}),
            {**BASIC_CHARM_METADATA_DICT, "maintainers": ["someone@company.com"]},
        ),
        (
            dict(**BASIC_CHARM_DICT, links={"contact": ["someone@company.com"]}),
            {**BASIC_CHARM_METADATA_DICT, "maintainers": ["someone@company.com"]},
        ),
        pytest.param(
            dict(
                **BASIC_CHARM_DICT,
                links={"issues": "https://github.com/canonical/charmcraft/issues"},
            ),
            {
                **BASIC_CHARM_METADATA_DICT,
                "issues": "https://github.com/canonical/charmcraft/issues",
            },
            id="non-transformed-link",
        ),
        (
            dict(**BASIC_CHARM_DICT, title="Title becomes display name"),
            {**BASIC_CHARM_METADATA_DICT, "display-name": "Title becomes display name"},
        ),
        pytest.param(
            {**BASIC_CHARM_DICT, "charm-user": "sudoer"},
            {**BASIC_CHARM_METADATA_DICT, "charm-user": "sudoer"},
            id="sudoer",
        ),
    ],
)
def test_charm_metadata_from_charm_success(charm_dict, expected):
    charm = project.CharmcraftProject.unmarshal(charm_dict)

    assert json.loads(json.dumps(metadata.CharmMetadata.from_charm(charm).marshal())) == expected


@pytest.mark.parametrize(
    ("bundle_dict", "expected"),
    [
        (BASIC_BUNDLE_DICT, BASIC_BUNDLE_METADATA_DICT),
    ],
)
def test_bundle_metadata_from_bundle(bundle_dict, expected):
    bundle = project.Bundle.unmarshal(BASIC_BUNDLE_DICT)

    assert (
        json.loads(json.dumps(metadata.BundleMetadata.from_bundle(bundle).marshal())) == expected
    )
