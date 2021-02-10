# Copyright 2020-2021 Canonical Ltd.
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

# empty namespace
noargs = Namespace()


@pytest.fixture
def bundle_yaml(tmp_path):
    """Create an empty bundle.yaml, with the option to set values to it."""
    bundle_path = tmp_path / 'bundle.yaml'
    bundle_path.write_text("{}")
    content = {}

    def func(*, name):
        content['name'] = name
        encoded = yaml.dump(content)
        bundle_path.write_text(encoded)
        return encoded

    return func


# -- tests for main building process

def test_simple_succesful_build(tmp_path, caplog, bundle_yaml, config):
    """A simple happy story."""
    caplog.set_level(logging.INFO, logger="charmcraft.commands")

    content = bundle_yaml(name='testbundle')
    config.set(type='bundle')

    # build!
    PackCommand('group', config).run(noargs)

    # check
    zipname = tmp_path / 'testbundle.zip'
    zf = zipfile.ZipFile(str(zipname))  # str() for Py3.5 support
    assert 'charmcraft.yaml' not in [x.filename for x in zf.infolist()]
    assert zf.read('bundle.yaml') == content.encode('ascii')

    expected = "Created '{}'.".format(zipname)
    assert [expected] == [rec.message for rec in caplog.records]


def test_missing_bundle_file(tmp_path, config):
    """Can not build a bundle without bundle.yaml."""
    # build without a bundle.yaml!
    with pytest.raises(CommandError) as cm:
        PackCommand('group', config).run(noargs)
    assert str(cm.value) == (
        "Missing or invalid main bundle file: '{}'.".format(tmp_path / 'bundle.yaml'))


def test_missing_name_in_bundle(tmp_path, bundle_yaml, config):
    """Can not build a bundle without name."""
    config.set(type='bundle')

    # build!
    with pytest.raises(CommandError) as cm:
        PackCommand('group', config).run(noargs)
    assert str(cm.value) == (
        "Invalid bundle config; missing a 'name' field indicating the bundle's name in file '{}'."
        .format(tmp_path / 'bundle.yaml'))


def test_bad_type_in_charmcraft(bundle_yaml, config):
    """The charmcraft.yaml file must have a proper type field."""
    bundle_yaml(name='testbundle')
    config.set(type='charm')

    # build!
    with pytest.raises(CommandError) as cm:
        PackCommand('group', config).run(noargs)
    assert str(cm.value) == (
        "Bad config: 'type' field in charmcraft.yaml must be 'bundle' for this command.")


# -- tests for get paths helper

def test_getpaths_mandatory_ok(tmp_path, config):
    """Simple succesful case getting all mandatory files."""
    test_mandatory = ['foo.txt', 'bar.bin']
    test_file1 = (tmp_path / 'foo.txt')
    test_file1.touch()
    test_file2 = (tmp_path / 'bar.bin')
    test_file2.touch()

    with patch.object(pack, 'MANDATORY_FILES', test_mandatory):
        result = get_paths_to_include(config)

    assert result == [test_file2, test_file1]


def test_getpaths_extra_ok(tmp_path, caplog, config):
    """Extra files were indicated ok."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    config.set(prime=['f2.txt', 'f1.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()
    testfile2 = tmp_path / 'f2.txt'
    testfile2.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(config)
    assert result == [testfile1, testfile2]

    expected = [
        "Including per prime config 'f2.txt': {}.".format([testfile2]),
        "Including per prime config 'f1.txt': {}.".format([testfile1]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_missing(tmp_path, caplog, config):
    """Extra files were indicated but not found."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    config.set(prime=['f2.txt', 'f1.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(config)
    assert result == [testfile1]

    expected = [
        "Including per prime config 'f2.txt': [].",
        "Including per prime config 'f1.txt': {}.".format([testfile1]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_long_path(tmp_path, config):
    """An extra file can be deep in directories."""
    config.set(prime=['foo/bar/baz/extra.txt'])
    testfile = tmp_path / 'foo' / 'bar' / 'baz' / 'extra.txt'
    testfile.parent.mkdir(parents=True)
    testfile.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(config)
    assert result == [testfile]


def test_getpaths_extra_wildcards_ok(tmp_path, caplog, config):
    """Use wildcards to specify several files ok."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    config.set(prime=['*.txt'])
    testfile1 = tmp_path / 'f1.txt'
    testfile1.touch()
    testfile2 = tmp_path / 'f2.bin'
    testfile2.touch()
    testfile3 = tmp_path / 'f3.txt'
    testfile3.touch()

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(config)
    assert result == [testfile1, testfile3]

    expected = [
        "Including per prime config '*.txt': {}.".format([testfile1, testfile3]),
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_wildcards_not_found(tmp_path, caplog, config):
    """Use wildcards to specify several files but nothing found."""
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    config.set(prime=['*.txt'])

    with patch.object(pack, 'MANDATORY_FILES', []):
        result = get_paths_to_include(config)
    assert result == []

    expected = [
        "Including per prime config '*.txt': [].",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_getpaths_extra_globstar(tmp_path, config):
    """Double star means whatever directories are in the path."""
    config.set(prime=['lib/**/*'])
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
        result = get_paths_to_include(config)
    assert result == sorted(allexpected)


def test_getpaths_extra_globstar_specific_files(tmp_path, config):
    """Combination of both mechanisms."""
    config.set(prime=['lib/**/*.txt'])
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
        result = get_paths_to_include(config)
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
