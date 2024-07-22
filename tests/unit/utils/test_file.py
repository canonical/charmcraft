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
"""Unit tests for file-related utilities."""
import os
import pathlib
import sys
import zipfile

import pytest
from craft_cli import CraftError

from charmcraft.utils.file import build_zip, make_executable, useful_filepath


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_make_executable_read_bits(tmp_path):
    pth = tmp_path / "test"
    pth.touch(mode=0o640)
    # validity check
    assert pth.stat().st_mode & 0o777 == 0o640
    with pth.open() as fd:
        make_executable(fd)
        # only read bits got made executable
        assert pth.stat().st_mode & 0o777 == 0o750


def test_usefulfilepath_pathlib(tmp_path):
    """Convert the string to Path."""
    test_file = tmp_path / "testfile.bin"
    test_file.touch()
    path = useful_filepath(str(test_file))
    assert path == test_file
    assert isinstance(path, pathlib.Path)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_usefulfilepath_home_expanded(tmp_path, monkeypatch):
    """Home-expand the indicated path."""
    fake_home = tmp_path / "homedir"
    fake_home.mkdir()
    test_file = fake_home / "testfile.bin"
    test_file.touch()

    monkeypatch.setitem(os.environ, "HOME", str(fake_home))
    path = useful_filepath("~/testfile.bin")
    assert path == test_file


def test_usefulfilepath_missing():
    """The indicated path is not there."""
    with pytest.raises(CraftError) as cm:
        useful_filepath("not_really_there.txt")
    assert str(cm.value) == "Cannot access 'not_really_there.txt'."


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_usefulfilepath_inaccessible(tmp_path):
    """The indicated path is not readable."""
    test_file = tmp_path / "testfile.bin"
    test_file.touch(mode=0o000)
    with pytest.raises(CraftError) as cm:
        useful_filepath(str(test_file))
    assert str(cm.value) == f"Cannot access {str(test_file)!r}."


def test_usefulfilepath_not_a_file(tmp_path):
    """The indicated path is not a file."""
    with pytest.raises(CraftError) as cm:
        useful_filepath(str(tmp_path))
    assert str(cm.value) == f"{str(tmp_path)!r} is not a file."


def test_zipbuild_simple(tmp_path):
    """Build a bunch of files in the zip."""
    build_dir = tmp_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "foo.txt"
    testfile1.write_bytes(b"123\x00456")
    subdir = build_dir / "bar"
    subdir.mkdir()
    testfile2 = subdir / "baz.txt"
    testfile2.write_bytes(b"mo\xc3\xb1o")

    zip_filepath = tmp_path / "testresult.zip"
    build_zip(zip_filepath, build_dir)

    zf = zipfile.ZipFile(zip_filepath)
    assert sorted(x.filename for x in zf.infolist()) == ["bar/baz.txt", "foo.txt"]
    assert zf.read("foo.txt") == b"123\x00456"
    assert zf.read("bar/baz.txt") == b"mo\xc3\xb1o"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_zipbuild_symlinks(tmp_path: pathlib.Path):
    """Symlinks are supported."""
    build_dir = tmp_path / "somedir"
    build_dir.mkdir()

    outside_dir = tmp_path / "another_dir"
    outside_dir.mkdir()
    outside_file = outside_dir / "some_file"
    outside_file.write_bytes(b"123\x00456")

    internal_dir = build_dir / "subdirectory"
    internal_dir.mkdir()
    real_file = internal_dir / "real.txt"
    real_file.write_bytes(b"123\x00456")

    internal_file_link = build_dir / "link.txt"
    internal_file_link.symlink_to(real_file)

    internal_dir_link = build_dir / "link_dir"
    internal_dir_link.symlink_to(internal_dir)

    external_file_link = build_dir / "external_link.txt"
    external_file_link.symlink_to(outside_file)

    external_dir_link = build_dir / "external_link_dir"
    external_dir_link.symlink_to(outside_dir)

    zip_filepath = tmp_path / "testresult.zip"
    build_zip(zip_filepath, build_dir)

    zf = zipfile.ZipFile(zip_filepath)

    expected_files = [
        "external_link.txt",
        "external_link_dir/some_file",
        "link.txt",
        "link_dir/real.txt",
        "subdirectory/real.txt",
    ]

    assert sorted(x.filename for x in zf.infolist()) == expected_files
    for file_name in expected_files:
        assert zf.read(file_name) == b"123\x00456"
