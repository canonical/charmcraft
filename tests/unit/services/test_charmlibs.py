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
import pytest_mock

from charmcraft import utils
from charmcraft.services.charmlibs import CharmLibDelta, CharmLibsService
from charmcraft.store.models import Library


@pytest.fixture
def service(service_factory):
    return service_factory.get("charm_libs")


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


def test_is_downloaded_no_file(
    fake_project_dir: pathlib.Path,
    service: CharmLibsService,
    charm_name: str,
    lib_name: str,
    api: int,
    patch: int | None,
):
    assert not service.is_downloaded(
        charm_name=charm_name, lib_name=lib_name, api=api, patch=patch
    )


@pytest.mark.parametrize(("patch", "expected"), [(None, True), (1, True), (2, False)])
def test_is_downloaded_with_file(
    project_path: pathlib.Path,
    service: CharmLibsService,
    charm_name: str,
    lib_name: str,
    patch: int | None,
    expected: bool,
):
    lib_path = project_path / utils.get_lib_path(charm_name, lib_name, 0)
    lib_path.parent.mkdir(parents=True)
    lib_path.write_text("LIBID='abc'\nLIBAPI=0\nLIBPATCH=1\n")

    assert (
        service.is_downloaded(
            charm_name=charm_name, lib_name=lib_name, api=0, patch=patch
        )
        == expected
    )


@pytest.mark.parametrize(
    ("charm_name", "lib_name", "lib_contents", "expected"),
    [
        pytest.param(
            "my-charm",
            "my_lib",
            "LIBID='abc'\nLIBAPI=0\nLIBPATCH=1\n",
            (0, 1),
            id="0.1",
        ),
        pytest.param(
            "my-charm",
            "my_lib",
            "LIBID='abc'\nLIBAPI=16\nLIBPATCH=19\n",
            (16, 19),
            id="16.19",
        ),
        pytest.param(
            "my-charm",
            "my_lib",
            "LIBID='abc'\nLIBAPI=0\nLIBPATCH=-1\n",
            None,
            id="patch_negative_1",
        ),
        pytest.param("my-charm", "my_lib", None, None, id="nonexistent"),
    ],
)
def test_get_local_version(
    project_path: pathlib.Path,
    service: CharmLibsService,
    charm_name: str,
    lib_name: str,
    lib_contents: str | None,
    expected: tuple[int, int] | None,
):
    if expected is not None:
        lib_path = project_path / utils.get_lib_path(charm_name, lib_name, expected[0])
        (project_path / lib_path).parent.mkdir(parents=True)
        (project_path / lib_path).write_text(str(lib_contents))

    assert (
        service.get_local_version(charm_name=charm_name, lib_name=lib_name) == expected
    )


@pytest.mark.parametrize(
    "lib",
    [
        Library("lib_id", "lib_name", "charm_name", 0, 0, "some content", "hashy"),
    ],
)
def test_write_success(
    project_path: pathlib.Path, service: CharmLibsService, lib: Library
):
    service.write(lib)

    actual = (
        project_path / utils.get_lib_path(lib.charm_name, lib.lib_name, lib.api)
    ).read_text()

    assert actual == lib.content


@pytest.mark.parametrize(
    "lib",
    [
        Library("lib_id", "lib_name", "charm_name", 0, 0, None, "hashy"),
    ],
)
def test_write_error(
    fake_project_dir: pathlib.Path, service: CharmLibsService, lib: Library
):
    with pytest.raises(ValueError, match="Library has no content"):
        service.write(lib)


@pytest.mark.parametrize(
    ("store_libs", "expected"),
    [
        pytest.param(
            {
                "abc": Library(
                    "abc",
                    "test-lib",
                    "charmcraft-test-charm",
                    0,
                    1000,
                    content=None,
                    content_hash="hash",
                )
            },
            [],
            id="all-up-to-date",
        ),
        pytest.param(
            {}, [CharmLibDelta("test_lib", (0, 1000), None)], id="all-unpublished"
        ),
        pytest.param(
            {
                "abc": Library(
                    "abc",
                    "test-lib",
                    "charmcraft-test-charm",
                    0,
                    999,
                    content=None,
                    content_hash="hash",
                )
            },
            [CharmLibDelta("test_lib", (0, 1000), (0, 999))],
            id="out-of-date",
        ),
    ],
)
def test_get_unpublished_libs(
    fake_project_dir: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    service: CharmLibsService,
    mocker: pytest_mock.MockerFixture,
    store_libs: dict[str, Library],
    expected: list[CharmLibDelta],
):
    service._project_dir = fake_project_dir
    local_lib_dir = fake_project_dir / "lib/charms/example_charm/v0"
    local_lib_dir.mkdir(parents=True)
    local_lib_file = local_lib_dir / "test_lib.py"
    local_lib_file.write_text("LIBID='abc'\nLIBAPI=0\nLIBPATCH=1000")

    mocker.patch.object(
        service._services.get("store"),
        "get_libraries_metadata_by_id",
        return_value=store_libs,
    )

    assert service.get_unpublished_libs() == expected
