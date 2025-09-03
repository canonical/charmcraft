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
"""Integration tests for charmlibs service."""

import pytest

from charmcraft.services.charmlibs import CharmLibDelta, CharmLibsService
from charmcraft.store.models import Library


@pytest.fixture
def service(service_factory):
    return service_factory.get("charm_libs")


# This test is marked as slow because it hits the real charmhub.
@pytest.mark.slow
@pytest.mark.parametrize(
    ("local_libs", "expected"),
    [
        pytest.param({}, [], id="no-libs"),
        pytest.param(
            {
                "lib/charms/example_charm/v0/test_lib.py": 'LIBID = "e000776021fd4b73ade744727654ac72"\nLIBAPI = 0\nLIBPATCH = 1'
            },
            [],
            id="up-to-date-lib",
        ),
        pytest.param(
            {
                "lib/charms/example_charm/v0/unpublished_lib.py": 'LIBID = "unpublished"\nLIBAPI = 0\nLIBPATCH = 1'
            },
            [CharmLibDelta("unpublished_lib", (0, 1), None)],
            id="unpublished-lib",
        ),
        pytest.param(
            {
                "lib/charms/example_charm/v0/test_lib.py": 'LIBID = "e000776021fd4b73ade744727654ac72"\nLIBAPI = 0\nLIBPATCH = 2'
            },
            [CharmLibDelta("test_lib", (0, 2), (0, 1))],
            id="out-of-date-lib",
        ),
    ],
)
def test_get_unpublished_libs(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    service: CharmLibsService,
    local_libs: dict[str, Library],
    expected: list[CharmLibDelta],
):
    service._project_dir = tmp_path
    for lib_path_str, lib_contents in local_libs.items():
        lib_path = tmp_path / lib_path_str
        lib_path.parent.mkdir(parents=True)
        lib_path.write_text(lib_contents)

    assert service.get_unpublished_libs() == expected
