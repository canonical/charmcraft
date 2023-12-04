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
"""Tests for Manifest model."""
import datetime

import pytest

from charmcraft.linters import CheckResult, CheckType
from charmcraft.models.charmcraft import Base
from charmcraft.models.manifest import Attribute, Manifest

SIMPLE_MANIFEST = Manifest(
    charmcraft_started_at="1970-01-01T00:00:00+00:00",
    bases=[Base(name="ubuntu", channel="22.04", architectures=["arm64"])],
)
MANIFEST_WITH_ATTRIBUTE = Manifest(
    **SIMPLE_MANIFEST.marshal(),
    analysis={"attributes": [Attribute(name="boop", result="success")]},
)


@pytest.mark.parametrize(
    ("lint", "expected"),
    [
        ([], SIMPLE_MANIFEST),
        ([CheckResult("lint", "lint", "lint", CheckType.LINT, "")], SIMPLE_MANIFEST),
        (
            [CheckResult("boop", "success", "", CheckType.ATTRIBUTE, "")],
            MANIFEST_WITH_ATTRIBUTE,
        ),
    ],
)
def test_from_charm_and_lint_success(simple_charm, lint, expected):
    simple_charm._started_at = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    assert Manifest.from_charm_and_lint(simple_charm, lint) == expected
