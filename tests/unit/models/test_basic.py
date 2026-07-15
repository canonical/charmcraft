# Copyright 2026 Canonical Ltd.
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
"""Tests for basic model types."""

import pydantic
import pytest

from charmcraft import linters
from charmcraft.models import basic, lint


class _NamesModel(pydantic.BaseModel):
    attribute: basic.AttributeName
    linter: basic.LinterName


class _AttributeChecker:
    check_type = lint.CheckType.ATTRIBUTE
    name = "language"


class _LinterChecker:
    check_type = lint.CheckType.LINT
    name = "juju-config"


@pytest.fixture
def fake_checkers(monkeypatch):
    monkeypatch.setattr(linters, "CHECKERS", [_AttributeChecker, _LinterChecker])


def test_validate_names(fake_checkers):
    model = _NamesModel.model_validate({"attribute": "language", "linter": "juju-config"})

    assert model == _NamesModel(attribute="language", linter="juju-config")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("attribute", "framework", "Bad attribute name 'framework'"),
        ("linter", "framework", "Bad lint name 'framework'"),
    ],
)
def test_validate_names_unknown(fake_checkers, field, value, match):
    with pytest.raises(pydantic.ValidationError, match=match):
        _NamesModel.model_validate({"attribute": "language", "linter": "juju-config", field: value})


def test_validate_names_strict(fake_checkers):
    with pytest.raises(pydantic.ValidationError, match="Input should be a valid string"):
        _NamesModel.model_validate({"attribute": 1, "linter": "juju-config"})
