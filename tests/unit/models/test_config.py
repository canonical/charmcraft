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
"""Tests for the config model."""
import math

import pydantic
import pytest

from charmcraft.models.config import (
    JujuBooleanOption,
    JujuConfig,
    JujuFloatOption,
    JujuIntOption,
    JujuStringOption,
)


@pytest.mark.parametrize(
    "options",
    [
        None,
        {},
        {
            "favourite integer": {"type": "int"},
            "favourite number": {"type": "float", "default": math.pi},
            "catchphrase": {"type": "string", "description": "What's your catchphrase?"},
            "default_answer": {
                "type": "boolean",
                "description": "Yes/no true or false",
                "default": True,
            },
        },
    ],
)
def test_valid_config(options):
    assert JujuConfig.model_validate({"options": options}) == JujuConfig(options=options)


def test_empty_config():
    JujuConfig.model_validate({})


@pytest.mark.parametrize(
    ("option", "type_"),
    [
        ({"type": "int"}, JujuIntOption),
        ({"type": "float"}, JujuFloatOption),
        ({"type": "string"}, JujuStringOption),
        ({"type": "boolean"}, JujuBooleanOption),
        ({"type": "float", "default": 0}, JujuFloatOption),
    ],
)
def test_correct_option_type(option, type_):
    config = JujuConfig(options={"my-opt": option})

    assert isinstance(config.options["my-opt"], type_)


@pytest.mark.parametrize(
    ("option", "match"),
    [
        (None, "Input should be a valid dict"),
        ({}, "Unable to extract tag using discriminator 'type'"),
        (
            {"type": "stargate"},
            "Input tag 'stargate' found using 'type' does not match any of the expected tags:",
        ),
        ({"type": "int", "default": 3.14}, "Input should be a valid integer"),
        ({"type": "float", "default": "pi"}, "Input should be a valid number"),
        ({"type": "boolean", "default": "maybe"}, "Input should be a valid boolean"),
    ],
)
def test_invalid_options(option, match):
    with pytest.raises(pydantic.ValidationError, match=match):
        JujuConfig(options={"my-opt": option})
