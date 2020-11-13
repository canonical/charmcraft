# Copyright 2020 Canonical Ltd.
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

import logging
import pathlib
import zipfile
from argparse import Namespace
from unittest.mock import patch

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands import pack
from charmcraft.commands.pack import (
    PackCommand,
    build_zip,
    get_paths_to_include,
)


@pytest.fixture
def bundle_yaml(tmp_path):
    """Create an empty bundle.yaml, with the option to set values to it."""
    bundle_path = tmp_path / 'bundle.yaml'
    bundle_path.write_text("{}")
    content = {}

    class _Setter:
        """Simple interface to have a .set in the fixture."""

        def set(self, *, name):
            content['name'] = name
            encoded = yaml.dump(content)
            bundle_path.write_text(encoded)
            return encoded

    return _Setter()


@pytest.fixture
def charmcraft_yaml(tmp_path):
    """Create an empty charmcraft.yaml, with the option to set values to it."""
    charmcraft_path = tmp_path / 'charmcraft.yaml'
    charmcraft_path.write_text("{}")
    content = {}

    class _Setter:
        """Simple interface to have a .set in the fixture."""

        def set(self, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            prime = kwargs.pop('prime', None)
            if prime is not None:
                content['parts'] = {
                    'bundle': {
                        'prime': prime,
                    }
                }

            # the rest is direct
            content.update(kwargs)

            encoded = yaml.dump(content)
            charmcraft_path.write_text(encoded)
            return encoded

    return _Setter()


# -- tests for main building process

def test_simple_succesful_build(tmp_path, caplog, bundle_yaml, charmcraft_yaml):
    """A simple happy story."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    content = bundle_yaml.set(name='testbundle')
    charmcraft_yaml.set(type='bundle')

    # build!
    args = Namespace(from_dir=tmp_path)
    PackCommand('group').run(args)

    # check
    zipname = tmp_path / 'testbundle.zip'
    zf = zipfile.ZipFile(str(zipname))  # str() for Py3.5 support
    assert 'charmcraft.yaml' not in [x.filename for x in zf.infolist()]
    assert zf.read('bundle.yaml') == content.encode('ascii')

    expected = "Done, bundle left in '{}'.".format(zipname)
    assert [expected] == [rec.message for rec in caplog.records]


def test_simple_build_directory_default(
        tmp_path, caplog, monkeypatch, bundle_yaml, charmcraft_yaml):
    """Building defaults to current directory."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")
    monkeypatch.chdir(tmp_path)

    # needed files
    content = bundle_yaml.set(name='testbundle')
    charmcraft_yaml.set(type='bundle')

    # build!
    args = Namespace(from_dir=None)
    PackCommand('group').run(args)

    # check
    zipname = tmp_path / 'testbundle.zip'
    zf = zipfile.ZipFile(str(zipname))  # str() for Py3.5 support
    assert zf.read('bundle.yaml') == content.encode('ascii')

    expected = "Done, bundle left in '{}'.".format(zipname)
    assert [expected] == [rec.message for rec in caplog.records]


def test_specified_directory_not_found(tmp_path):
    """The specified directory is not there."""
    not_there = tmp_path / 'not there'
    args = Namespace(from_dir=not_there)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == "Bundle project directory was not found: '{}'.".format(not_there)


def test_specified_directory_not_a_directory(tmp_path):
    """The specified directory is not really a directory."""
    somefile = tmp_path / 'somefile'
    somefile.touch()
    args = Namespace(from_dir=somefile)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == (
        "Bundle project directory is not really a directory: '{}'.".format(somefile))


def test_missing_bundle_file(tmp_path, charmcraft_yaml):
    """Can not build a bundle without bundle.yaml."""
    # build without a bundle.yaml!
    args = Namespace(from_dir=tmp_path)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == (
        "Missing or invalid main bundle file: '{}'.".format(tmp_path / 'bundle.yaml'))


def test_missing_charmcraft_file(tmp_path, bundle_yaml):
    """Can not build a bundle without charmcraft.yaml."""
    bundle_yaml.set(name='testbundle')

    # build without a charmcraft.yaml!
    args = Namespace(from_dir=tmp_path)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == (
        "Missing or invalid charmcraft file: '{}'.".format(tmp_path / 'charmcraft.yaml'))


def test_missing_name_in_bundle(tmp_path, bundle_yaml, charmcraft_yaml):
    """Can not build a bundle without name."""
    charmcraft_yaml.set(type='bundle')

    # build!
    args = Namespace(from_dir=tmp_path)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == (
        "Invalid bundle config; missing a 'name' field indicating the bundle's name in file '{}'."
        .format(tmp_path / 'bundle.yaml'))


def test_missing_type_in_charmcraft(tmp_path, bundle_yaml, charmcraft_yaml):
    """The charmcraft.yaml file must have a proper type field."""
    bundle_yaml.set(name='testbundle')

    # build!
    args = Namespace(from_dir=tmp_path)
    with pytest.raises(CommandError) as cm:
        PackCommand('group').run(args)
    assert str(cm.value) == (
        "Invalid charmcraft config; 'type' must be 'bundle' in file '{}'."
        .format(tmp_path / 'charmcraft.yaml'))


# -- tests for get paths helper

def test_getpaths_mandatory_ok(tmp_path):
    """Simple succesful case getting all mandatory files."""
    test_mandatory = ['foo.txt', 'bar.bin']
    test_file1 = (tmp_path / 'foo.txt')
    test_file1.touch()
    test_file2 = (tmp_path / 'bar.bin')
    test_file2.touch()

    with patch.object(pack, 'MANDATORY_FILES', test_mandatory):
        result = get_paths_to_include(tmp_path)

    assert result == [test_file2, test_file1]


def test_getpaths_extra_ok(tmp_path, caplog, charmcraft_yaml):
    """Extra files were indicated ok."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    charmcraft_yaml.set(prime=['f2.txt', 'f1.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()
    testfile2 = tmp_path / 'f2.txt'
    testfile2.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == [testfile1, testfile2]

    expected = [
        "Including per prime config 'f2.txt': {}.".format([testfile2]),
        "Including per prime config 'f1.txt': {}.".format([testfile1]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_missing(tmp_path, caplog, charmcraft_yaml):
    """Extra files were indicated but not found."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    charmcraft_yaml.set(prime=['f2.txt', 'f1.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == [testfile1]

    expected = [
        "Including per prime config 'f2.txt': [].",
        "Including per prime config 'f1.txt': {}.".format([testfile1]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_absolute(tmp_path, charmcraft_yaml):
    """All extra files must be relative to the project."""
    charmcraft_yaml.set(prime=['/tmp/foobar'])
    with patch.object(pack, 'MANDATORY_FILES', []):
        with pytest.raises(CommandError) as cm:
            get_paths_to_include(tmp_path)
    assert str(cm.value) == "Extra files in prime config can not be absolute: '/tmp/foobar'"


def test_getpaths_extra_long_path(tmp_path, charmcraft_yaml):
    """An extra file can be deep in directories."""
    charmcraft_yaml.set(prime=['foo/bar/baz/extra.txt'])
    testfile = tmp_path / 'foo' / 'bar' / 'baz' / 'extra.txt'
    testfile.parent.mkdir(parents=True)
    testfile.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == [testfile]


def test_getpaths_extra_wildcards_ok(tmp_path, caplog, charmcraft_yaml):
    """Use wildcards to specify several files ok."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    charmcraft_yaml.set(prime=['*.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()
    testfile2 = tmp_path / 'f2.bin'
    testfile2.touch()
    testfile3 = tmp_path / 'f3.txt'
    testfile3.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == [testfile1, testfile3]

    expected = [
        "Including per prime config '*.txt': {}.".format([testfile1, testfile3]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_wildcards_not_found(tmp_path, caplog, charmcraft_yaml):
    """Use wildcards to specify several files but nothing found."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    charmcraft_yaml.set(prime=['*.txt'])

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == []

    expected = [
        "Including per prime config '*.txt': [].",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_globstar(tmp_path, charmcraft_yaml):
    """Double star means whatever directories are in the path."""
    charmcraft_yaml.set(prime=['lib/**/*'])
    srcpaths = (
        ('lib/foo/f1.txt', True),
        ('lib/foo/deep/fx.txt', True),
        ('lib/bar/f2.txt', True),
        ('lib/f3.txt', True),
        ('extra/lib/f.txt', False),
        ('libs/fs.txt', False),
    )
    allexpected = []
    for srcpath, expected in srcpaths:
        testfile = tmp_path / pathlib.Path(srcpath)
        testfile.parent.mkdir(parents=True, exist_ok=True)
        testfile.touch()
        if expected:
            allexpected.append(testfile)

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == sorted(allexpected)


def test_getpaths_extra_globstar_specific_files(tmp_path, charmcraft_yaml):
    """Combination of both mechanisms."""
    charmcraft_yaml.set(prime=['lib/**/*.txt'])
    srcpaths = (
        ('lib/foo/f1.txt', True),
        ('lib/foo/f1.nop', False),
        ('lib/foo/deep/fx.txt', True),
        ('lib/foo/deep/fx.nop', False),
        ('lib/bar/f2.txt', True),
        ('lib/bar/f2.nop', False),
        ('lib/f3.txt', True),
        ('lib/f3.nop', False),
        ('extra/lib/f.txt', False),
        ('libs/fs.nop', False),
    )
    allexpected = []
    for srcpath, expected in srcpaths:
        testfile = tmp_path / pathlib.Path(srcpath)
        testfile.parent.mkdir(parents=True, exist_ok=True)
        testfile.touch()
        if expected:
            allexpected.append(testfile)

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(tmp_path)
    assert result == sorted(allexpected)


# -- tests for zip builder

def test_zipbuild_simple(tmp_path):
    """Build a bunch of files in the zip."""
    testfile1 = tmp_path / 'foo.txt'
    testfile1.write_bytes(b"123\x00456")
    subdir = tmp_path / 'bar'
    subdir.mkdir()
    testfile2 = subdir / 'baz.txt'
    testfile2.write_bytes(b"mo\xc3\xb1o")

    zip_filepath = tmp_path / 'testresult.zip'
    build_zip(zip_filepath, tmp_path, [testfile1, testfile2])

    zf = zipfile.ZipFile(str(zip_filepath))  # str() for Py3.5 support
    assert sorted(x.filename for x in zf.infolist()) == ['bar/baz.txt', 'foo.txt']
    assert zf.read('foo.txt') == b"123\x00456"
    assert zf.read('bar/baz.txt') == b"mo\xc3\xb1o"


def test_zipbuild_symlink_simple(tmp_path):
    """Symlinks are supported."""
    testfile1 = tmp_path / 'real.txt'
    testfile1.write_bytes(b"123\x00456")
    testfile2 = tmp_path / 'link.txt'
    testfile2.symlink_to(testfile1)

    zip_filepath = tmp_path / 'testresult.zip'
    build_zip(zip_filepath, tmp_path, [testfile1, testfile2])

    zf = zipfile.ZipFile(str(zip_filepath))  # str() for Py3.5 support
    assert sorted(x.filename for x in zf.infolist()) == ['link.txt', 'real.txt']
    assert zf.read('real.txt') == b"123\x00456"
    assert zf.read('link.txt') == b"123\x00456"


def test_zipbuild_symlink_outside(tmp_path):
    """No matter where the symlink points to."""
    # outside the build dir
    testfile1 = tmp_path / 'real.txt'
    testfile1.write_bytes(b"123\x00456")

    # inside the build dir
    build_dir = tmp_path / 'somedir'
    build_dir.mkdir()
    testfile2 = build_dir / 'link.txt'
    testfile2.symlink_to(testfile1)

    zip_filepath = tmp_path / 'testresult.zip'
    build_zip(zip_filepath, build_dir, [testfile2])

    zf = zipfile.ZipFile(str(zip_filepath))  # str() for Py3.5 support
    assert sorted(x.filename for x in zf.infolist()) == ['link.txt']
    assert zf.read('link.txt') == b"123\x00456"
