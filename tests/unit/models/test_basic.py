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
"""Tests for basic models."""
import re

import pytest

from charmcraft.models import basic


@pytest.mark.parametrize(
    "name", ["os", "postgresql.postgres_client", "PyYAML", "lib.v2.thing"]
)
def test_module_name_regex_valid(name):
    assert basic.PythonModuleName.regex.match(name)


@pytest.mark.parametrize(
    "name", ["1", "package-name"]
)
def test_module_name_regex_invalid(name):
    assert not basic.PythonModuleName.regex.match(name)
