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
import pathlib

import pytest
import yaml

from charmcraft import const
from charmcraft.errors import DuplicateCharmsError, InvalidCharmPathError
from charmcraft.utils.project import find_charm_sources, get_charm_name_from_path

BASIC_CHARM_MAP = {
    "charm1": pathlib.Path("charms/charm1/"),
    "charm2": pathlib.Path("charms/charm2/"),
    "operator1": pathlib.Path("operators/operator1"),
    "operator2": pathlib.Path("operators/operator2"),
    "basic": pathlib.Path("basic"),
    "basic2": pathlib.Path("basic2"),
}


def test_find_charm_sources_empty_directory(tmp_path):
    actual = find_charm_sources(tmp_path, ["a", "b", "c"])

    assert actual == {}


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_finds_values(tmp_path, fake_charms, build_charm_directory):
    expected = build_charm_directory(tmp_path, fake_charms)

    actual = find_charm_sources(tmp_path, fake_charms.keys())

    assert actual == expected


@pytest.mark.parametrize(
    "fake_charms",
    [{"basic": pathlib.Path("charms/basic"), "basic2": pathlib.Path("charms/basic2")}],
)
def test_find_charm_sources_with_symlinks(tmp_path, build_charm_directory, fake_charms):
    symlinks_path = tmp_path / "operators"
    symlinks_path.mkdir()
    expected = build_charm_directory(tmp_path, fake_charms)
    for name, path in fake_charms.items():
        (symlinks_path / name).symlink_to(tmp_path / path, target_is_directory=True)

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == expected


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_extra_charms(tmp_path, build_charm_directory, fake_charms):
    expected = build_charm_directory(tmp_path, fake_charms)
    invalid_charm = tmp_path / "charms/invalid"
    build_charm_directory(tmp_path, {"invalid": invalid_charm})

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == expected


@pytest.mark.parametrize("fake_charms", [BASIC_CHARM_MAP])
def test_find_charm_sources_non_matching_path(tmp_path, build_charm_directory, fake_charms):
    charms = {name: path.with_name(f"non_matching_{name}") for name, path in fake_charms.items()}
    build_charm_directory(tmp_path, charms)

    actual = find_charm_sources(tmp_path, fake_charms)

    assert actual == {}


def test_find_charm_sources_duplicates(check, tmp_path, build_charm_directory):
    fake_charms = {"charm1": pathlib.Path("charm1")}
    build_charm_directory(tmp_path, fake_charms)
    build_charm_directory(tmp_path, {"charm1": pathlib.Path("charms/charm1")})
    build_charm_directory(tmp_path, {"charm1": pathlib.Path("operators/charm1")})
    expected = DuplicateCharmsError(
        {
            "charm1": [
                pathlib.Path("charm1"),
                pathlib.Path("charms/charm1"),
                pathlib.Path("operators/charm1"),
            ]
        }
    )

    with pytest.raises(DuplicateCharmsError) as exc_info:
        find_charm_sources(tmp_path, fake_charms)

    check.equal(exc_info.value.args, expected.args)
    check.equal(exc_info.value.resolution, expected.resolution)


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_success(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path})

    actual = get_charm_name_from_path(tmp_path / path)

    assert actual == name


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_bundle(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path}, file_type="bundle")
    full_path = tmp_path / path

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"


@pytest.mark.parametrize(
    ("name", "path", "del_file"),
    [
        ("test1", "test1", const.CHARMCRAFT_FILENAME),
        ("test1", "charms/test1", const.METADATA_FILENAME),
        ("test1", "operators/test1", const.CHARMCRAFT_FILENAME),
    ],
)
def test_get_charm_name_from_path_missing_file(
    tmp_path, build_charm_directory, name, path, del_file
):
    build_charm_directory(tmp_path, {name: path})
    full_path = tmp_path / path
    (full_path / del_file).unlink()

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("test1", "test1"),
        ("test1", "charms/test1"),
        ("test1", "operators/test1"),
    ],
)
def test_get_charm_name_from_path_wrong_name(tmp_path, build_charm_directory, name, path):
    build_charm_directory(tmp_path, {name: path}, file_type="bundle")
    full_path = tmp_path / path
    with (full_path / const.METADATA_FILENAME).open("w") as file:
        yaml.safe_dump({"naam": "not a name"}, file)

    with pytest.raises(InvalidCharmPathError) as exc_info:
        get_charm_name_from_path(full_path)

    assert exc_info.value.args[0] == f"Path does not contain source for a valid charm: {full_path}"
