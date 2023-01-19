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
from pytest_check import check
from craft_cli import CraftError

from charmcraft.commands.store.charmlibs import get_positive_int, get_lib_info


class TestGetPositiveInt:
    """Tests for get_positive_int."""

    @pytest.mark.parametrize(
        ["raw_value", "expected"],
        [
            pytest.param("1", 1),
            pytest.param(b"0", 0),
        ],
    )
    def test_success(self, raw_value, expected):
        assert get_positive_int(raw_value) == expected

    @pytest.mark.parametrize(
        ["raw_value", "error_class", "error_regex"],
        [
            pytest.param("123.456", ValueError, "invalid literal"),
            pytest.param("-1", ValueError, "negative"),
            pytest.param(b"", ValueError, "invalid literal", id="empty-bytes"),
        ],
    )
    def test_exceptions(self, raw_value, error_class, error_regex):
        """Test various exceptions that can be passed through."""
        with pytest.raises(error_class, match=error_regex):
            get_positive_int(raw_value)


class TestGetLibInfo:
    """Tests for get_lib_info."""

    @pytest.fixture(autouse=True)
    def charm_path(self, tmp_path, monkeypatch):
        """Monkey-patched tmp_path for charms.
        This fixture is set to auto-use so that each function gets a tempdir.
        """
        monkeypatch.chdir(tmp_path)
        yield tmp_path

    @staticmethod
    def create_lib(extra_content=None, metadata_id=None, metadata_api=None, metadata_patch=None):
        """Helper to create the structures on disk for a given lib.

        WARNING: this function has the capability of creating INCORRECT structures on disk.

        This is specific for the get_lib_info tests below, other tests should use the
        functionality provided by the factory.
        """
        base_path = pathlib.Path("lib")
        lib_file = base_path / "charms" / "testcharm" / "v3" / "testlib.py"
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

    def test_success_simple(self, charm_path):
        """Simple basic case of success getting info from the library."""
        test_path = self.create_lib()

        lib_data = get_lib_info(lib_path=test_path)
        with check:
            assert lib_data.lib_id == "test-lib-id"
        with check:
            assert lib_data.api == 3
        with check:
            assert lib_data.patch == 14
        with check:
            assert lib_data.content_hash is not None
        with check:
            assert lib_data.content is not None
        with check:
            assert lib_data.full_name == "charms.testcharm.v3.testlib"
        with check:
            assert lib_data.path == test_path
        with check:
            assert lib_data.lib_name == "testlib"
        with check:
            assert lib_data.charm_name == "testcharm"

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
    @pytest.mark.parametrize(
        "extra_content",
        [
            pytest.param("Some\nnew\r\nlines\n!", id="Newlines"),
            pytest.param("ñáéíóú", id="non-ascii"),
            pytest.param("\0", id="non-printable"),
        ],
    )
    def test_success_content(self, charm_path, monkeypatch, extra_content):
        """Check that content and its hash are ok."""
        test_path = self.create_lib(extra_content=extra_content)

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
    def test_bad_name(self, name):
        """Different combinations of a bad library name."""
        name_match = (
            rf"^Charm library name {name!r} must conform to charms\.<charm>\.vN\.<libname>$"
        )
        with pytest.raises(CraftError, match=name_match):
            get_lib_info(full_name=name)

    def test_not_importable_charm_name(self):
        """Libraries should be save under importable paths."""
        lib_data = get_lib_info(full_name="charms.operator-libs-linux.v0.apt")
        with check:
            assert lib_data.charm_name == "operator-libs-linux"
        with check:
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
    def test_bad_path(self, path):
        """Different combinations of a bad library path."""
        path_match = (
            rf"^Charm library path {path} must conform to lib/charms/<charm>/vN/<libname>\.py$"
        )
        with pytest.raises(CraftError, match=path_match):
            get_lib_info(lib_path=pathlib.Path(path))

    @pytest.mark.parametrize(
        "name",
        [
            "charms.testcharm.v-three.testlib",
            "charms.testcharm.v-3.testlib",
            "charms.testcharm.3.testlib",
            "charms.testcharm.vX.testlib",
        ],
    )
    def test_bad_api(self, name):
        """Different combinations of a bad api in the path/name."""
        match = r"^The API version in the library path must be 'vN' where N is an integer\.$"
        with pytest.raises(CraftError, match=match):
            get_lib_info(full_name=name)

    def test_missing_library_from_name(self):
        """Partial case for when the library is not found in disk, starting from the name."""
        test_name = "charms.testcharm.v3.testlib"
        # no create lib!
        lib_data = get_lib_info(full_name=test_name)
        with check:
            assert lib_data.lib_id is None
        with check:
            assert lib_data.api == 3
        with check:
            assert lib_data.patch == -1
        with check:
            assert lib_data.content_hash is None
        with check:
            assert lib_data.content is None
        with check:
            assert lib_data.full_name == test_name
        with check:
            assert (
                lib_data.path == pathlib.Path("lib") / "charms" / "testcharm" / "v3" / "testlib.py"
            )
        with check:
            assert lib_data.lib_name == "testlib"
        with check:
            assert lib_data.charm_name == "testcharm"

    def test_missing_library_from_path(self):
        """Partial case for when the library is not found in disk, starting from the path."""
        test_path = pathlib.Path("lib") / "charms" / "testcharm" / "v3" / "testlib.py"
        # no create lib!
        lib_data = get_lib_info(lib_path=test_path)
        with check:
            assert lib_data.lib_id is None
        with check:
            assert lib_data.api == 3
        with check:
            assert lib_data.patch == -1
        with check:
            assert lib_data.content_hash is None
        with check:
            assert lib_data.content is None
        with check:
            assert lib_data.full_name == "charms.testcharm.v3.testlib"
        with check:
            assert lib_data.path == test_path
        with check:
            assert lib_data.lib_name == "testlib"
        with check:
            assert lib_data.charm_name == "testcharm"

    @pytest.mark.parametrize(
        "fields,match",
        [
            pytest.param(
                {"metadata_id": "LIBID = foo = 23"},
                r"^Bad metadata line in '.+testlib.py': b'LIBID = foo = 23\\n'$",
                id="malformed ID",
            ),
            pytest.param(
                {"metadata_patch": "", "metadata_api": ""},
                r"^Library '.+' is missing the mandatory metadata fields: LIBAPI, LIBPATCH\.$",
                id="missing api and patch",
            ),
        ],
    )
    @pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
    def test_invalid_metadata_field(self, charm_path, fields, match):
        """Some metadata field is not really valid."""
        test_path = self.create_lib(**fields)
        with pytest.raises(CraftError, match=match):
            get_lib_info(lib_path=test_path)

    bad_field_match = r"^Library .+ metadata field {} is not zero or a positive integer\.$"

    @pytest.mark.parametrize(
        "lib_fields,match",
        [
            pytest.param(
                {"metadata_api": "LIBAPI = v3"},
                bad_field_match.format("LIBAPI"),
                id="API non-integer",
            ),
            pytest.param(
                {"metadata_api": "LIBAPI = -3"},
                bad_field_match.format("LIBAPI"),
                id="API negative",
            ),
            pytest.param(
                {"metadata_patch": "LIBPATCH = beta3"},
                bad_field_match.format("LIBPATCH"),
                id="PATCH non-integer",
            ),
            pytest.param(
                {"metadata_patch": "LIBPATCH = -1"},
                bad_field_match.format("LIBPATCH"),
                id="PATCH negative",
            ),
            pytest.param(
                {"metadata_api": "LIBAPI = 0", "metadata_patch": "LIBPATCH = 0"},
                r"^Library .+ metadata fields LIBAPI and LIBPATCH cannot both be zero\.$",
                id="API and PATCH both zero",
            ),
        ],
    )
    def test_api_patch_invalid(self, lib_fields, match):
        """Invalid values for API or patch versions."""
        test_path = self.create_lib(**lib_fields)
        with pytest.raises(CraftError, match=match):
            get_lib_info(lib_path=test_path)

    def test_metadata_api_different_path_api(
        self,
    ):
        """The API value included in the file is different from the one in the path."""
        test_path = self.create_lib(metadata_api="LIBAPI = 99")
        match = r"^Library .+ metadata field LIBAPI is different from the version in the path\.$"
        with pytest.raises(CraftError, match=match):
            get_lib_info(lib_path=test_path)

    @pytest.mark.parametrize(
        "metadata_id",
        [
            pytest.param("LIBID = 99", id="Non-string"),
            pytest.param("LIBID = 'moño'", id="Non-ASCII"),
            pytest.param("LIBID = ''", id="empty"),
        ],
    )
    def test_libid_invalid(self, metadata_id):
        """The ID is not really a string."""
        test_path = self.create_lib(metadata_id=metadata_id)
        match = r"Library .+ metadata field LIBID must be a non-empty ASCII string\."
        with pytest.raises(CraftError, match=match):
            get_lib_info(lib_path=test_path)
