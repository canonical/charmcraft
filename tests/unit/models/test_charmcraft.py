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
"""Tests for Charmcraft models."""
import pytest

from charmcraft.models import charmcraft


@pytest.mark.parametrize(
    ("base_str", "expected"),
    [
        ("ubuntu@24.04", charmcraft.Base(name="ubuntu", channel="24.04", architectures=[])),
        ("ubuntu@22.04", charmcraft.Base(name="ubuntu", channel="22.04", architectures=[])),
        ("almalinux@9", charmcraft.Base(name="almalinux", channel="9", architectures=[])),
    ],
)
def test_get_base_from_str_and_arch(base_str, expected):
    assert charmcraft.Base.from_str_and_arch(base_str, []) == expected
