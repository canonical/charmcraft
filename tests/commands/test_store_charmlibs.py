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

"""Tests for store helpers commands (code in store/charmlibs.py)."""
import hashlib
import pathlib
import sys

import pytest
from craft_cli import CraftError

from charmcraft.commands.store.charmlibs import get_lib_info, get_name_from_metadata


# region Name-related tests
def test_get_name_from_metadata_ok(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a valid metadata
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wb") as fh:
        fh.write(b"name: test-name")

    result = get_name_from_metadata()
    assert result == "test-name"


def test_get_name_from_metadata_no_file(tmp_path, monkeypatch):
    """No metadata file to get info."""
    monkeypatch.chdir(tmp_path)
    result = get_name_from_metadata()
    assert result is None


def test_get_name_from_metadata_bad_content_garbage(tmp_path, monkeypatch):
    """The metadata file is broken."""
    monkeypatch.chdir(tmp_path)

    # put a broken metadata
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wb") as fh:
        fh.write(b"\b00\bff -- not a really yaml stuff")

    result = get_name_from_metadata()
    assert result is None


def test_get_name_from_metadata_bad_content_no_name(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a broken metadata
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wb") as fh:
        fh.write(b"{}")

    result = get_name_from_metadata()
    assert result is None


# endregion
# region getlibinfo tests


def _create_lib(extra_content=None, metadata_id=None, metadata_api=None, metadata_patch=None):
    """Helper to create the structures on disk for a given lib.
    WARNING: this function has the capability of creating INCORRECT structures on disk.
    This is specific for the _get_lib_info tests below, other tests should use the
    functionality provided by the factory.
    """
    base_dir = pathlib.Path("lib")
    lib_file = base_dir / "charms" / "testcharm" / "v3" / "testlib.py"
    lib_file.parent.mkdir(parents=True, exist_ok=True)

    # save the content to that specific file under custom structure
    if metadata_id is None:
        metadata_id = "LIBID = 'test-lib-id'"
    if metadata_api is None:
        metadata_api = "LIBAPI = 3"
    if metadata_patch is None:
        metadata_patch = "LIBPATCH = 14"

    fields = [metadata_id, metadata_api, metadata_patch]
    with lib_file.open("wt", encoding="utf8") as fh:
        for f in fields:
            if f:
                fh.write(f + "\n")
        if extra_content:
            fh.write(extra_content)

    return lib_file


def test_getlibinfo_success_simple(tmp_path, monkeypatch):
    """Simple basic case of success getting info from the library."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib()

    lib_data = get_lib_info(lib_path=test_path)
    assert lib_data.lib_id == "test-lib-id"
    assert lib_data.api == 3
    assert lib_data.patch == 14
    assert lib_data.content_hash is not None
    assert lib_data.content is not None
    assert lib_data.full_name == "charms.testcharm.v3.testlib"
    assert lib_data.path == test_path
    assert lib_data.lib_name == "testlib"
    assert lib_data.charm_name == "testcharm"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_getlibinfo_success_content(tmp_path, monkeypatch):
    """Check that content and its hash are ok."""
    monkeypatch.chdir(tmp_path)
    extra_content = """
        extra lines for the file
        extra non-ascii: ñáéíóú
        the content is everything, this plus metadata
        the hash should be of this, excluding metadata
    """
    test_path = _create_lib(extra_content=extra_content)

    lib_data = get_lib_info(lib_path=test_path)
    assert lib_data.content == test_path.read_text()
    assert lib_data.content_hash == hashlib.sha256(extra_content.encode("utf8")).hexdigest()


@pytest.mark.parametrize(
    "name",
    [
        "charms.testcharm.v3.testlib.py",
        "charms.testcharm.testlib",
        "testcharm.v2.testlib",
        "mycharms.testcharm.v2.testlib",
    ],
)
def test_getlibinfo_bad_name(name):
    """Different combinations of a bad library name."""
    with pytest.raises(CraftError) as err:
        get_lib_info(full_name=name)
    assert str(err.value) == (
        "Charm library name {!r} must conform to charms.<charm>.vN.<libname>".format(name)
    )


def test_getlibinfo_not_importable_charm_name():
    """Libraries should be save under importable paths."""
    lib_data = get_lib_info(full_name="charms.operator-libs-linux.v0.apt")
    assert lib_data.charm_name == "operator-libs-linux"
    assert lib_data.path == pathlib.Path("lib/charms/operator_libs_linux/v0/apt.py")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "path",
    [
        "charms/testcharm/v3/testlib",
        "charms/testcharm/v3/testlib.html",
        "charms/testcharm/v3/testlib.",
        "charms/testcharm/testlib.py",
        "testcharm/v2/testlib.py",
        "mycharms/testcharm/v2/testlib.py",
    ],
)
def test_getlibinfo_bad_path(path):
    """Different combinations of a bad library path."""
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=pathlib.Path(path))
    assert str(err.value) == (
        "Charm library path {} must conform to lib/charms/<charm>/vN/<libname>.py".format(path)
    )


@pytest.mark.parametrize(
    "name",
    [
        "charms.testcharm.v-three.testlib",
        "charms.testcharm.v-3.testlib",
        "charms.testcharm.3.testlib",
        "charms.testcharm.vX.testlib",
    ],
)
def test_getlibinfo_bad_api(name):
    """Different combinations of a bad api in the path/name."""
    with pytest.raises(CraftError) as err:
        get_lib_info(full_name=name)
    assert str(err.value) == (
        "The API version in the library path must be 'vN' where N is an integer."
    )


def test_getlibinfo_missing_library_from_name():
    """Partial case for when the library is not found in disk, starting from the name."""
    test_name = "charms.testcharm.v3.testlib"
    # no create lib!
    lib_data = get_lib_info(full_name=test_name)
    assert lib_data.lib_id is None
    assert lib_data.api == 3
    assert lib_data.patch == -1
    assert lib_data.content_hash is None
    assert lib_data.content is None
    assert lib_data.full_name == test_name
    assert lib_data.path == pathlib.Path("lib") / "charms" / "testcharm" / "v3" / "testlib.py"
    assert lib_data.lib_name == "testlib"
    assert lib_data.charm_name == "testcharm"


def test_getlibinfo_missing_library_from_path():
    """Partial case for when the library is not found in disk, starting from the path."""
    test_path = pathlib.Path("lib") / "charms" / "testcharm" / "v3" / "testlib.py"
    # no create lib!
    lib_data = get_lib_info(lib_path=test_path)
    assert lib_data.lib_id is None
    assert lib_data.api == 3
    assert lib_data.patch == -1
    assert lib_data.content_hash is None
    assert lib_data.content is None
    assert lib_data.full_name == "charms.testcharm.v3.testlib"
    assert lib_data.path == test_path
    assert lib_data.lib_name == "testlib"
    assert lib_data.charm_name == "testcharm"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_getlibinfo_malformed_metadata_field(tmp_path, monkeypatch):
    """Some metadata field is not really valid."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id="LIBID = foo = 23")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == r"Bad metadata line in {!r}: b'LIBID = foo = 23\n'".format(
        str(test_path)
    )


def test_getlibinfo_missing_metadata_field(tmp_path, monkeypatch):
    """Some metadata field is not present."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="", metadata_api="")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} is missing the mandatory metadata fields: LIBAPI, LIBPATCH.".format(
            str(test_path)
        )
    )


def test_getlibinfo_api_not_int(tmp_path, monkeypatch):
    """The API is not an integer."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_api="LIBAPI = v3")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBAPI is not zero or a positive integer.".format(
            str(test_path)
        )
    )


def test_getlibinfo_api_negative(tmp_path, monkeypatch):
    """The API is not negative."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_api="LIBAPI = -3")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBAPI is not zero or a positive integer.".format(
            str(test_path)
        )
    )


def test_getlibinfo_patch_not_int(tmp_path, monkeypatch):
    """The PATCH is not an integer."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="LIBPATCH = beta3")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBPATCH is not zero or a positive integer.".format(
            str(test_path)
        )
    )


def test_getlibinfo_patch_negative(tmp_path, monkeypatch):
    """The PATCH is not negative."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="LIBPATCH = -1")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBPATCH is not zero or a positive integer.".format(
            str(test_path)
        )
    )


def test_getlibinfo_api_patch_both_zero(tmp_path, monkeypatch):
    """Invalid combination of both API and PATCH being 0."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="LIBPATCH = 0", metadata_api="LIBAPI = 0")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata fields LIBAPI and LIBPATCH cannot both be zero.".format(
            str(test_path)
        )
    )


def test_getlibinfo_metadata_api_different_path_api(tmp_path, monkeypatch):
    """The API value included in the file is different than the one in the path."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_api="LIBAPI = 99")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBAPI is different from the version in the path.".format(
            str(test_path)
        )
    )


def test_getlibinfo_libid_non_string(tmp_path, monkeypatch):
    """The ID is not really a string."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id="LIBID = 99")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBID must be a non-empty ASCII string.".format(
            str(test_path)
        )
    )


def test_getlibinfo_libid_non_ascii(tmp_path, monkeypatch):
    """The ID is not ASCII."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id="LIBID = 'moño'")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBID must be a non-empty ASCII string.".format(
            str(test_path)
        )
    )


def test_getlibinfo_libid_empty(tmp_path, monkeypatch):
    """The ID is empty."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id="LIBID = ''")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        "Library {!r} metadata field LIBID must be a non-empty ASCII string.".format(
            str(test_path)
        )
    )


# endregion
