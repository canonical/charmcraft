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
"""Tests for store helpers."""
from hypothesis import given, strategies

from charmcraft import utils


@given(charms=strategies.lists(strategies.text()), bundles=strategies.lists(strategies.text()))
def test_get_packages(charms, bundles):
    packages = utils.get_packages(charms=charms, bundles=bundles)
    result_names = [package.package_name for package in packages]
    assert result_names == charms + bundles
