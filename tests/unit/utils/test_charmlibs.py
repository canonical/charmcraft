# Copyright 2023-2024 Canonical Ltd.
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

from charmcraft import const
from charmcraft.utils.charmlibs import (
    collect_charmlib_pydeps,
    get_lib_info,
    get_lib_internals,
    get_lib_module_name,
    get_lib_path,
    get_libs_from_tree,
    get_name_from_metadata,
)


# region Name-related tests
def test_get_name_from_metadata_ok(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a valid metadata
    metadata_file = tmp_path / const.METADATA_FILENAME
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
    metadata_file = tmp_path / const.METADATA_FILENAME
    with metadata_file.open("wb") as fh:
        fh.write(b"\b00\bff -- not a really yaml stuff")

    result = get_name_from_metadata()
    assert result is None


def test_get_name_from_metadata_bad_content_no_name(tmp_path, monkeypatch):
    """The metadata file is valid yaml, but there is no name."""
    monkeypatch.chdir(tmp_path)

    # put a broken metadata
    metadata_file = tmp_path / const.METADATA_FILENAME
    with metadata_file.open("wb") as fh:
        fh.write(b"{}")

    result = get_name_from_metadata()
    assert result is None


@pytest.mark.parametrize(
    ("charm", "lib", "api", "expected"),
    [
        ("my-charm", "some_lib", 0, pathlib.Path("lib/charms/my_charm/v0/some_lib.py")),
    ],
)
def test_get_lib_path(charm: str, lib: str, api: int, expected: pathlib.Path):
    assert get_lib_path(charm, lib, api) == expected


@pytest.mark.parametrize(
    ("charm", "lib", "api", "expected"),
    [
        ("my-charm", "some_lib", 0, "charms.my_charm.v0.some_lib"),
    ],
)
def test_get_lib_module_name(charm: str, lib: str, api: int, expected: str):
    assert get_lib_module_name(charm, lib, api) == expected


# endregion
# region getlibinfo tests


def _create_lib(
    extra_content=None,
    metadata_id=None,
    metadata_api=None,
    metadata_patch=None,
    pydeps=None,
    charm_name="testcharm",
    lib_name="testlib.py",
):
    """Helper to create the structures on disk for a given lib.

    WARNING: this function has the capability of creating INCORRECT structures on disk.
    This is specific for the _get_lib_info tests below, other tests should use the
    functionality provided by the factory.
    """
    base_dir = pathlib.Path("lib")
    lib_file = base_dir / "charms" / charm_name / "v3" / lib_name
    lib_file.parent.mkdir(parents=True, exist_ok=True)

    # save the content to that specific file under custom structure
    if metadata_id is None:
        metadata_id = "LIBID = 'test-lib-id'"
    if metadata_api is None:
        metadata_api = "LIBAPI = 3"
    if metadata_patch is None:
        metadata_patch = "LIBPATCH = 14"

    fields = [metadata_id, metadata_api, metadata_patch]
    if pydeps is not None:
        fields.append(pydeps)
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
        f"Charm library name {name!r} must conform to charms.<charm>.vN.<libname>"
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
        f"Charm library path {path} must conform to lib/charms/<charm>/vN/<libname>.py"
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


def test_getlibinfo_metadata_api_different_path_api(tmp_path, monkeypatch):
    """The API value included in the file is different than the one in the path."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_api="LIBAPI = 99")
    with pytest.raises(CraftError) as err:
        get_lib_info(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata field LIBAPI is different from the version in the path."
    )


# endregion
# region tests for get_lib_internals


def test_getlibinternals_success_simple(tmp_path, monkeypatch):
    """Simple basic case of success getting internals from the library."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib()
    internals = get_lib_internals(test_path)
    assert internals.lib_id == "test-lib-id"
    assert internals.api == 3
    assert internals.patch == 14
    assert internals.pydeps == []
    assert internals.content is not None
    assert internals.content_hash is not None


def test_getlibinternals_success_with_pydeps(tmp_path, monkeypatch):
    """Simple basic successful case that includes pydeps."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(pydeps="PYDEPS = ['foo', 'bar']")
    internals = get_lib_internals(test_path)
    assert internals.lib_id == "test-lib-id"
    assert internals.api == 3
    assert internals.patch == 14
    assert internals.pydeps == ["foo", "bar"]
    assert internals.content is not None
    assert internals.content_hash is not None


def test_getlibinternals_success_content(tmp_path, monkeypatch):
    """Check that content and its hash are ok."""
    extra_content = """
        # extra lines for the file
        # extra non-ascii: ñáéíóú
        # the content is everything, this plus metadata
        # the hash should be of this, excluding metadata
    """
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(extra_content=extra_content)

    internals = get_lib_internals(test_path)
    assert internals.content == test_path.read_text(encoding="utf8")
    assert internals.content_hash == hashlib.sha256(extra_content.encode("utf8")).hexdigest()


def test_getlibinternals_non_toplevel_names(tmp_path, monkeypatch):
    """Test non direct assignments."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(extra_content="logging.getLogger('kazoo.client').disabled = True")
    internals = get_lib_internals(test_path)

    assert internals.lib_id == "test-lib-id"
    assert internals.api == 3
    assert internals.patch == 14
    assert internals.pydeps == []
    assert internals.content is not None
    assert internals.content_hash is not None


def test_getlibinternals_malformed_content(tmp_path, monkeypatch):
    """Some internals field is not really valid."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(extra_content="  broken \n    python  ")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == rf"Failed to parse Python library {str(test_path)!r}"


@pytest.mark.parametrize(
    ("empty_args", "missing"),
    [
        (["metadata_id"], "LIBID"),
        (["metadata_api"], "LIBAPI"),
        (["metadata_patch"], "LIBPATCH"),
        (["metadata_id", "metadata_api"], "LIBAPI, LIBID"),
        (["metadata_patch", "metadata_api"], "LIBAPI, LIBPATCH"),
        (["metadata_patch", "metadata_id"], "LIBID, LIBPATCH"),
    ],
)
def test_getlibinternals_missing_internals_field(tmp_path, empty_args, missing, monkeypatch):
    """Some internals field is not present."""
    monkeypatch.chdir(tmp_path)
    kwargs = {arg: "" for arg in empty_args}
    test_path = _create_lib(**kwargs)
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} is missing the mandatory metadata fields: {missing}."
    )


@pytest.mark.parametrize("value", ["v3", "-3"])
def test_getlibinternals_api_bad_value(tmp_path, value, monkeypatch):
    """The API is not a positive integer."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_api=f"LIBAPI = {value}")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata field LIBAPI "
        "must be a constant assignment of zero or a positive integer."
    )


@pytest.mark.parametrize("value", ["beta3", "-1"])
def test_getlibinternals_patch_bad_value(tmp_path, value, monkeypatch):
    """The PATCH is not a positive integer."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="LIBPATCH = {value}")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata field LIBPATCH "
        "must be a constant assignment of zero or a positive integer."
    )


def test_getlibinternals_api_patch_both_zero(tmp_path, monkeypatch):
    """Invalid combination of both API and PATCH being 0."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_patch="LIBPATCH = 0", metadata_api="LIBAPI = 0")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata fields LIBAPI and LIBPATCH cannot both be zero."
    )


@pytest.mark.parametrize("value", [99, "moño", ""])
def test_getlibinternals_libid_bad_value(tmp_path, value, monkeypatch):
    """The ID is not really a ASCII nonempty string."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id=f"LIBID = {value!r}")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata field LIBID "
        "must be a constant assignment of a non-empty ASCII string."
    )


def test_getlibinternals_pydeps_complex(tmp_path, monkeypatch):
    """The PYDEPS field can be multiline, unicode, different quotes."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(
        pydeps="""PYDEPS = [
        'foo',
        "bar",
        "moño",
    ]"""
    )
    internals = get_lib_internals(test_path)
    assert internals.lib_id == "test-lib-id"
    assert internals.api == 3
    assert internals.patch == 14
    assert internals.pydeps == ["foo", "bar", "moño"]
    assert internals.content is not None
    assert internals.content_hash is not None


@pytest.mark.parametrize(
    "value",
    [
        "'foo'",  # a string
        "33",  # other object
        "open()",  # generic code
        "('foo', 'bar')",  # a tuple
        "['foo', 33]",  # a list with wrong fields inside
        "['foo', otherdep]",  # a list with wrong fields inside
    ],
)
def test_getlibinternals_pydeps_bad_value(tmp_path, value, monkeypatch):
    """Different cases with invalid PYDEPS."""
    monkeypatch.chdir(tmp_path)
    test_path = _create_lib(metadata_id=f"PYDEPS = {value}")
    with pytest.raises(CraftError) as err:
        get_lib_internals(lib_path=test_path)
    assert str(err.value) == (
        f"Library {str(test_path)!r} metadata field PYDEPS "
        "must be a constant list of non-empty strings"
    )


# endregion
# region get libs from tree tests


def test_getlibsfromtree_named_currentdir(tmp_path, monkeypatch):
    """Get libs for a specific charm in the current directory."""
    monkeypatch.chdir(tmp_path)
    test_path_1 = _create_lib(charm_name="charm1", lib_name="testlib1.py")
    test_path_2 = _create_lib(charm_name="charm1", lib_name="testlib2.py")
    _create_lib(charm_name="charm2", lib_name="testlib3.py")
    libs_data = get_libs_from_tree(charm_name="charm1")
    assert {data.path for data in libs_data} == {test_path_1, test_path_2}


def test_getlibsfromtree_everything_currentdir(tmp_path, monkeypatch):
    """Get libs for a specific charm in the current directory."""
    monkeypatch.chdir(tmp_path)
    test_path_1 = _create_lib(charm_name="charm1", lib_name="testlib1.py")
    test_path_2 = _create_lib(charm_name="charm1", lib_name="testlib2.py")
    test_path_3 = _create_lib(charm_name="charm2", lib_name="testlib3.py")
    libs_data = get_libs_from_tree()
    assert {data.path for data in libs_data} == {test_path_1, test_path_2, test_path_3}


def test_getlibsfromtree_named_otherdir(tmp_path, monkeypatch):
    """Get libs for a specific charm in other directory."""
    otherdir = tmp_path / "otherdir"
    otherdir.mkdir()
    monkeypatch.chdir(otherdir)
    test_path_1 = _create_lib(charm_name="charm1", lib_name="testlib1.py")
    test_path_2 = _create_lib(charm_name="charm1", lib_name="testlib2.py")
    monkeypatch.chdir(tmp_path)
    _create_lib(charm_name="charm2", lib_name="testlib3.py")
    libs_data = get_libs_from_tree(charm_name="charm1", root=otherdir)
    assert {data.path for data in libs_data} == {test_path_1, test_path_2}


def test_getlibsfromtree_everything_otherdir(tmp_path, monkeypatch):
    """Get libs for a specific charm in other directory."""
    otherdir = tmp_path / "otherdir"
    otherdir.mkdir()
    monkeypatch.chdir(otherdir)
    test_path_1 = _create_lib(charm_name="charm1", lib_name="testlib1.py")
    test_path_2 = _create_lib(charm_name="charm1", lib_name="testlib2.py")
    test_path_3 = _create_lib(charm_name="charm2", lib_name="testlib3.py")
    monkeypatch.chdir(tmp_path)
    libs_data = get_libs_from_tree(root=otherdir)
    assert {data.path for data in libs_data} == {test_path_1, test_path_2, test_path_3}


# endregion
# region pydeps collection tests


def test_collectpydeps_generic(tmp_path, monkeypatch):
    """Collect the PYDEPS from all libs from all charms."""
    otherdir = tmp_path / "otherdir"
    otherdir.mkdir()
    monkeypatch.chdir(otherdir)
    _create_lib(charm_name="charm1", lib_name="lib1.py", pydeps="PYDEPS = ['foo', 'bar']")
    _create_lib(charm_name="charm1", lib_name="lib2.py", pydeps="PYDEPS = ['bar']")
    _create_lib(charm_name="charm2", lib_name="lib3.py")
    _create_lib(charm_name="charm2", lib_name="lib3.py", pydeps="PYDEPS = ['baz']")
    monkeypatch.chdir(tmp_path)
    charmlib_deps = collect_charmlib_pydeps(otherdir)
    assert charmlib_deps == {"foo", "bar", "baz"}


# endregion
