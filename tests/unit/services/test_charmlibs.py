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
"""Unit tests for charmlibs service."""

import pathlib
import pytest
import pytest_check

from charmcraft import services, utils
from charmcraft.store.models import Library


@pytest.fixture
def service(service_factory):
    return service_factory.charm_libs


@pytest.fixture(params=["my-charm", "your-charm"])
def charm_name(request) -> str:
    return request.param


@pytest.fixture(params=["my_lib", "your_lib"])
def lib_name(request) -> str:
    return request.param


@pytest.fixture(params=[0, 1])
def api(request) -> int:
    return request.param


@pytest.fixture(params=[None, 0, 1])
def patch(request) -> int | None:
    return request.param


def test_is_lib_downloaded_no_file(fake_project_dir: pathlib.Path, service: services.CharmLibsService, charm_name: str, lib_name: str, api: int, patch: int | None):
    assert not service.is_lib_downloaded(
        charm_name=charm_name, lib_name=lib_name, api=api, patch=patch
    )


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        (None, True),
        (1, True),
        (2, False)
    ]
)
def test_is_lib_downloaded_with_file(fake_project_dir: pathlib.Path, service: services.CharmLibsService, charm_name: str, lib_name: str, patch: int | None, expected: bool):
    lib_path = fake_project_dir / utils.get_lib_path(charm_name, lib_name, 0)
    lib_path.parent.mkdir(parents=True)
    lib_path.write_text("LIBID='abc'\nLIBAPI=0\nLIBPATCH=1\n")

    assert service.is_lib_downloaded(charm_name=charm_name, lib_name=lib_name, api=0, patch=patch) == expected


@pytest.mark.parametrize(
    "lib",
    [
        Library("lib_id", "lib_name", "charm_name", 0, 0, "some content", "hashy"),
    ]
)
def test_write_lib_success(fake_project_dir: pathlib.Path, service: services.CharmLibsService, lib: Library):
    service.write_lib(lib)

    actual = (fake_project_dir / utils.get_lib_path(lib.charm_name, lib.lib_name, lib.api)).read_text()

    assert actual == lib.content


@pytest.mark.parametrize(
    "lib",
    [
        Library("lib_id", "lib_name", "charm_name", 0, 0, None, "hashy"),
    ]
)
def test_write_lib_error(fake_project_dir: pathlib.Path, service: services.CharmLibsService, lib: Library):
    with pytest.raises(ValueError, match="Library has no content"):
        service.write_lib(lib)
