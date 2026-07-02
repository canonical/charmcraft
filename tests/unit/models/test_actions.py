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
"""Tests for the JujuActions model."""

import pytest

from charmcraft.models.actions import JujuActions


def _actions(name):
    return {name: {"description": "x"}}


@pytest.mark.parametrize(
    "name",
    [
        "snapshot",
        "backup-database",
        "do-the-thing",
        "a",
        "a1",
        "step-1",
        "action2",
    ],
)
def test_valid_action_names(name):
    JujuActions(actions=_actions(name))


@pytest.mark.parametrize(
    "name",
    [
        "snake_case",
        "_leading-underscore",
        "trailing_",
        "Uppercase",
        "camelCase",
        "-leading-hyphen",
        "trailing-hyphen-",
        "has space",
        "with.dot",
        "",
    ],
)
def test_invalid_action_names_rejected(name):
    with pytest.raises(ValueError, match="is not a valid action name"):
        JujuActions(actions=_actions(name))


@pytest.mark.parametrize("name", ["if", "for", "class", "return"])
def test_python_keyword_action_names_rejected(name):
    with pytest.raises(ValueError, match="reserved keyword"):
        JujuActions(actions=_actions(name))


@pytest.mark.parametrize("body", ["a string", 42, None, ["a", "list"]])
def test_non_mapping_action_body_rejected(body):
    with pytest.raises(ValueError, match="valid dictionary"):
        JujuActions(actions={"do-thing": body})


def test_action_body_missing_description_rejected():
    with pytest.raises(ValueError, match="missing a description"):
        JujuActions(actions={"do-thing": {}})
