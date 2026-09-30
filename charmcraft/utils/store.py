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
"""Store helper utilities."""

from collections.abc import Iterable


def get_packages(
    charms: Iterable[str] = (), bundles: Iterable[str] = ()
) -> list[dict[str, str]]:
    """Get a list of package specs from charms and bundles.

    The store's token request API expects each package as a dict with
    "type" and "name" keys.
    """
    return [
        *({"type": "charm", "name": charm} for charm in charms),
        *({"type": "bundle", "name": bundle} for bundle in bundles),
    ]
