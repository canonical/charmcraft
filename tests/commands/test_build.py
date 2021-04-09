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

import errno
import filecmp
import logging
import pathlib
import os
import socket
import sys
import zipfile
from collections import namedtuple
from unittest.mock import patch, call

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands.build import (
    BUILD_DIRNAME,
    Builder,
    CHARM_METADATA,
    DISPATCH_CONTENT,
    DISPATCH_FILENAME,
    VENV_DIRNAME,
    Validator,
    polite_exec,
    relativise,
)


# --- Validator tests

def test_validator_process_simple():
    """Process the present options and store the result."""
    class TestValidator(Validator):
        _options = ['foo', 'bar']

        def validate_foo(self, arg):
            assert arg == 35
            return 70

        def validate_bar(self, arg):
            assert arg == 45
            return 80

    test_args = namedtuple('T', 'foo bar')(35, 45)
    validator = TestValidator()
    result = validator.process(test_args)
    assert result == dict(foo=70, bar=80)


def test_validator_process_notpresent():
    """Process an option after not finding the value."""
    class TestValidator(Validator):
        _options = ['foo']

        def validate_foo(self, arg):
            assert arg is None
            return 70

    test_args = namedtuple('T', 'bar')(35)
    validator = TestValidator()
    result = validator.process(test_args)
    assert result == dict(foo=70)


def test_validator_from_simple(tmp_path):
    """'from' param: simple validation and setting in Validation."""
    validator = Validator()
    resp = validator.validate_from(tmp_path)
    assert resp == tmp_path
    assert validator.basedir == tmp_path


def test_validator_from_default():
    """'from' param: default value."""
    validator = Validator()
    resp = validator.validate_from(None)
    assert resp == pathlib.Path('.').absolute()


def test_validator_from_absolutized(tmp_path, monkeypatch):
    """'from' param: check it's made absolute."""
    # change dir to the temp one, where we will have the 'dir1/dir2' tree
    dir1 = tmp_path / 'dir1'
    dir1.mkdir()
    dir2 = dir1 / 'dir2'
    dir2.mkdir()
    monkeypatch.chdir(tmp_path)

    validator = Validator()
    resp = validator.validate_from(pathlib.Path('dir1/dir2'))
    assert resp == dir2


def test_validator_from_expanded():
    """'from' param: expands the user-home prefix."""
    validator = Validator()
    resp = validator.validate_from(pathlib.Path('~'))
    assert resp == pathlib.Path.home()


def test_validator_from_exist():
    """'from' param: checks that the directory exists."""
    validator = Validator()
    expected_msg = "Charm directory was not found: '/not_really_there'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(pathlib.Path('/not_really_there'))


def test_validator_from_isdir(tmp_path):
    """'from' param: checks that the directory is really that."""
    testfile = tmp_path / 'testfile'
    testfile.touch()

    validator = Validator()
    expected_msg = "Charm directory is not really a directory: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(testfile)


def test_validator_entrypoint_simple(tmp_path):
    """'entrypoint' param: simple validation."""
    testfile = tmp_path / 'testfile'
    testfile.touch(mode=0o777)

    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(testfile)
    assert resp == testfile


def test_validator_entrypoint_default(tmp_path):
    """'entrypoint' param: default value."""
    default_entrypoint = tmp_path / 'src' / 'charm.py'
    default_entrypoint.parent.mkdir()
    default_entrypoint.touch(mode=0o777)

    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(None)
    assert resp == default_entrypoint


def test_validator_entrypoint_absolutized(tmp_path, monkeypatch):
    """'entrypoint' param: check it's made absolute."""
    # change dir to the temp one, where we will have the 'dirX/file.py' stuff
    dirx = tmp_path / 'dirX'
    dirx.mkdir()
    testfile = dirx / 'file.py'
    testfile.touch(mode=0o777)
    monkeypatch.chdir(tmp_path)

    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_entrypoint(pathlib.Path('dirX/file.py'))
    assert resp == testfile


def test_validator_entrypoint_expanded(tmp_path):
    """'entrypoint' param: expands the user-home prefix."""
    fake_home = tmp_path / 'homedir'
    fake_home.mkdir()

    testfile = fake_home / 'testfile'
    testfile.touch(mode=0o777)

    validator = Validator()
    validator.basedir = tmp_path

    with patch.dict(os.environ, {'HOME': str(fake_home)}):
        resp = validator.validate_entrypoint(pathlib.Path('~/testfile'))
    assert resp == testfile


def test_validator_entrypoint_exist():
    """'entrypoint' param: checks that the file exists."""
    validator = Validator()
    expected_msg = "Charm entry point was not found: '/not_really_there.py'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(pathlib.Path('/not_really_there.py'))


def test_validator_entrypoint_inside_project(tmp_path):
    """'entrypoint' param: checks that it's part of the project."""
    project_dir = tmp_path / 'test-project'
    testfile = tmp_path / 'testfile'
    testfile.touch(mode=0o777)

    validator = Validator()
    validator.basedir = project_dir

    expected_msg = "Charm entry point must be inside the project: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(testfile)


def test_validator_entrypoint_exec(tmp_path):
    """'entrypoint' param: checks that the file is executable."""
    testfile = tmp_path / 'testfile'
    testfile.touch(mode=0o444)

    validator = Validator()
    validator.basedir = tmp_path
    expected_msg = "Charm entry point must be executable: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(testfile)


def test_validator_requirement_simple(tmp_path):
    """'requirement' param: simple validation."""
    testfile = tmp_path / 'testfile'
    testfile.touch()

    validator = Validator()
    resp = validator.validate_requirement([testfile])
    assert resp == [testfile]


def test_validator_requirement_multiple(tmp_path):
    """'requirement' param: multiple files."""
    testfile1 = tmp_path / 'testfile1'
    testfile1.touch()
    testfile2 = tmp_path / 'testfile2'
    testfile2.touch()

    validator = Validator()
    resp = validator.validate_requirement([testfile1, testfile2])
    assert resp == [testfile1, testfile2]


def test_validator_requirement_default_present_ok(tmp_path):
    """'requirement' param: default value when a requirements.txt is there and readable."""
    default_requirement = tmp_path / 'requirements.txt'
    default_requirement.touch()

    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == [default_requirement]


def test_validator_requirement_default_present_not_readable(tmp_path):
    """'requirement' param: default value when a requirements.txt is there but not readable."""
    default_requirement = tmp_path / 'requirements.txt'
    default_requirement.touch(0o230)

    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == []


def test_validator_requirement_default_missing(tmp_path):
    """'requirement' param: default value when no requirements.txt is there."""
    validator = Validator()
    validator.basedir = tmp_path
    resp = validator.validate_requirement(None)
    assert resp == []


def test_validator_requirement_absolutized(tmp_path, monkeypatch):
    """'requirement' param: check it's made absolute."""
    # change dir to the temp one, where we will have the reqs file
    testfile = tmp_path / 'reqs.txt'
    testfile.touch()
    monkeypatch.chdir(tmp_path)

    validator = Validator()
    resp = validator.validate_requirement([pathlib.Path('reqs.txt')])
    assert resp == [testfile]


def test_validator_requirement_expanded(tmp_path):
    """'requirement' param: expands the user-home prefix."""
    fake_home = tmp_path / 'homedir'
    fake_home.mkdir()

    requirement = fake_home / 'requirements.txt'
    requirement.touch(0o230)

    validator = Validator()

    with patch.dict(os.environ, {'HOME': str(fake_home)}):
        resp = validator.validate_requirement([pathlib.Path('~/requirements.txt')])
    assert resp == [requirement]


def test_validator_requirement_exist():
    """'requirement' param: checks that the file exists."""
    validator = Validator()
    expected_msg = "the requirements file was not found: '/not_really_there.txt'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_requirement([pathlib.Path('/not_really_there.txt')])


# --- Polite Executor tests

def test_politeexec_base(caplog):
    """Basic execution."""
    caplog.set_level(logging.ERROR, logger="charmcraft")

    cmd = ['echo', 'HELO']
    retcode = polite_exec(cmd)
    assert retcode == 0
    assert not caplog.records


def test_politeexec_stdout_logged(caplog):
    """The standard output is logged in debug."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    cmd = ['echo', 'HELO']
    polite_exec(cmd)
    expected = [
        "Running external command ['echo', 'HELO']",
        ":: HELO",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_politeexec_stderr_logged(caplog):
    """The standard error is logged in debug."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    cmd = [sys.executable, '-c', "import sys; print('weird, huh?', file=sys.stderr)"]
    polite_exec(cmd)
    expected = [
        "Running external command " + str(cmd),
        ":: weird, huh?",
    ]
    assert expected == [rec.message for rec in caplog.records]


def test_politeexec_failed(caplog):
    """It's logged in error if cmd fails."""
    caplog.set_level(logging.ERROR, logger="charmcraft")

    cmd = [sys.executable, '-c', "exit(3)"]
    retcode = polite_exec(cmd)
    assert retcode == 3
    expected_msg = "Executing {} failed with return code 3".format(cmd)
    assert any(expected_msg in rec.message for rec in caplog.records)


def test_politeexec_crashed(caplog, tmp_path):
    """It's logged in error if cmd fails."""
    caplog.set_level(logging.ERROR, logger="charmcraft")
    nonexistent = tmp_path / 'whatever'

    cmd = [str(nonexistent)]
    retcode = polite_exec(cmd)
    assert retcode == 1
    expected_msg = "Executing {} crashed with FileNotFoundError".format(cmd)
    assert any(expected_msg in rec.message for rec in caplog.records)


# --- (real) build tests


def test_build_basic_complete_structure(tmp_path, monkeypatch):
    """Integration test: a simple structure with custom lib and normal src dir."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # the metadata (save it and restore to later check)
    metadata_data = {'name': 'name-from-metadata'}
    metadata_file = tmp_path / 'metadata.yaml'
    metadata_raw = yaml.dump(metadata_data).encode('ascii')
    with metadata_file.open('wb') as fh:
        fh.write(metadata_raw)

    # a lib dir
    lib_dir = tmp_path / 'lib'
    lib_dir.mkdir()
    ops_lib_dir = lib_dir / 'ops'
    ops_lib_dir.mkdir()
    ops_stuff = ops_lib_dir / 'stuff.txt'
    with ops_stuff.open('wb') as fh:
        fh.write(b'ops stuff')

    # simple source code
    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    charm_script = src_dir / 'charm.py'
    with charm_script.open('wb') as fh:
        fh.write(b'all the magic')

    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = Builder({
        'from': tmp_path,
        'entrypoint': charm_script,
        'requirement': [],
    })
    zipname = builder.run()

    # check all is properly inside the zip
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipname)
    assert zf.read('metadata.yaml') == metadata_raw
    assert zf.read('src/charm.py') == b"all the magic"
    dispatch = DISPATCH_CONTENT.format(entrypoint_relative_path='src/charm.py').encode('ascii')
    assert zf.read('dispatch') == dispatch
    assert zf.read('hooks/install') == dispatch
    assert zf.read('hooks/start') == dispatch
    assert zf.read('hooks/upgrade-charm') == dispatch
    assert zf.read('lib/ops/stuff.txt') == b"ops stuff"


def test_build_generics_simple_files(tmp_path):
    """Check transferred metadata and simple entrypoint, also return proper linked entrypoint."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    metadata.touch()
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    linked_entrypoint = builder.handle_generic_paths()

    # check files are there, are files, and are really hard links (so no
    # check for permissions needed)
    built_metadata = build_dir / CHARM_METADATA
    assert built_metadata.is_file()
    assert built_metadata.stat().st_ino == metadata.stat().st_ino

    built_entrypoint = build_dir / 'crazycharm.py'
    assert built_entrypoint.is_file()
    assert built_entrypoint.stat().st_ino == entrypoint.stat().st_ino

    assert linked_entrypoint == built_entrypoint


def test_build_generics_simple_dir(tmp_path):
    """Check transferred any directory, with proper permissions."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()

    somedir = tmp_path / 'somedir'
    somedir.mkdir(mode=0o700)

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    built_dir = build_dir / 'somedir'
    assert built_dir.is_dir()
    assert built_dir.stat().st_mode & 0xFFF == 0o700


def test_build_generics_ignored_file(tmp_path, caplog):
    """Don't include ignored filed."""
    caplog.set_level(logging.DEBUG)
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # create two files (and the needed entrypoint)
    file1 = tmp_path / 'file1.txt'
    file1.touch()
    file2 = tmp_path / 'file2.txt'
    file2.touch()
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })

    # set it up to ignore file 2 and make it work
    builder.ignore_rules.extend_patterns(['file2.*'])
    builder.handle_generic_paths()

    assert (build_dir / 'file1.txt').exists()
    assert not (build_dir / 'file2.txt').exists()

    expected = "Ignoring file because of rules: 'file2.txt'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_ignored_dir(tmp_path, caplog):
    """Don't include ignored dir."""
    caplog.set_level(logging.DEBUG)
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # create two files (and the needed entrypoint)
    dir1 = tmp_path / 'dir1'
    dir1.mkdir()
    dir2 = tmp_path / 'dir2'
    dir2.mkdir()
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })

    # set it up to ignore dir 2 and make it work
    builder.ignore_rules.extend_patterns(['dir2'])
    builder.handle_generic_paths()

    assert (build_dir / 'dir1').exists()
    assert not (build_dir / 'dir2').exists()

    expected = "Ignoring directory because of rules: 'dir2'"
    assert expected in [rec.message for rec in caplog.records]


def _test_build_generics_tree(tmp_path, caplog, *, expect_hardlinks):
    caplog.set_level(logging.DEBUG)

    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # create this structure:
    # ├─ crazycharm.py  (entrypoint)
    # ├─ file1.txt
    # ├─ dir1
    # │  └─ dir3  (ignored!)
    # └─ dir2
    #    ├─ file2.txt
    #    ├─ file3.txt  (ignored!)
    #    ├─ dir4  (ignored!)
    #    │   └─ file4.txt
    #    └─ dir5
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()
    file1 = tmp_path / 'file1.txt'
    file1.touch()
    dir1 = tmp_path / 'dir1'
    dir1.mkdir()
    dir3 = dir1 / 'dir3'
    dir3.mkdir()
    dir2 = tmp_path / 'dir2'
    dir2.mkdir()
    file2 = dir2 / 'file2.txt'
    file2.touch()
    file3 = dir2 / 'file3.txt'
    file3.touch()
    dir4 = dir2 / 'dir4'
    dir4.mkdir()
    file4 = dir4 / 'file4.txt'
    file4.touch()
    dir5 = dir2 / 'dir5'
    dir5.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })

    # set it up to ignore some stuff and make it work
    builder.ignore_rules.extend_patterns([
        'dir1/dir3',
        'dir2/file3.txt',
        'dir2/dir4',
    ])
    builder.handle_generic_paths()

    assert (build_dir / 'crazycharm.py').exists()
    assert (build_dir / 'file1.txt').exists()
    assert (build_dir / 'dir1').exists()
    assert not (build_dir / 'dir1' / 'dir3').exists()
    assert (build_dir / 'dir2').exists()
    assert (build_dir / 'dir2' / 'file2.txt').exists()
    assert not (build_dir / 'dir2' / 'file3.txt').exists()
    assert not (build_dir / 'dir2' / 'dir4').exists()
    assert (build_dir / 'dir2' / 'dir5').exists()

    for (p1, p2) in [
        (build_dir / 'crazycharm.py', entrypoint),
        (build_dir / 'file1.txt', file1),
        (build_dir / 'dir2' / 'file2.txt', file2),
    ]:
        if expect_hardlinks:
            # they're hard links
            assert p1.samefile(p2)
        else:
            # they're *not* hard links
            assert not p1.samefile(p2)
            # but they're essentially the same
            assert filecmp.cmp(str(p1), str(p2), shallow=False)
            assert p1.stat().st_mode == p2.stat().st_mode
            assert p1.stat().st_size == p2.stat().st_size
            assert p1.stat().st_atime == pytest.approx(p2.stat().st_atime)
            assert p1.stat().st_mtime == pytest.approx(p2.stat().st_mtime)


def test_build_generics_tree(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores."""
    _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=True)


def test_build_generics_tree_vagrant(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores, when hardlinks aren't allowed."""
    with patch('os.link') as mock_link:
        mock_link.side_effect = PermissionError("No you don't.")
        _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=False)


def test_build_generics_tree_xdev(tmp_path, caplog):
    """Manages ok a deep tree, including internal ignores, when hardlinks can't be done."""
    with patch('os.link') as mock_link:
        mock_link.side_effect = OSError(errno.EXDEV, os.strerror(errno.EXDEV))
        _test_build_generics_tree(tmp_path, caplog, expect_hardlinks=False)


def test_build_generics_symlink_file(tmp_path):
    """Respects a symlinked file."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()
    the_symlink = tmp_path / 'somehook.py'
    the_symlink.symlink_to(entrypoint)

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    built_symlink = build_dir / 'somehook.py'
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / 'crazycharm.py'
    real_link = os.readlink(str(built_symlink))
    assert real_link == 'crazycharm.py'


def test_build_generics_symlink_dir(tmp_path):
    """Respects a symlinked dir."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()
    somedir = tmp_path / 'somedir'
    somedir.mkdir()
    somefile = somedir / 'sanity check'
    somefile.touch()
    the_symlink = tmp_path / 'thelink'
    the_symlink.symlink_to(somedir)

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    built_symlink = build_dir / 'thelink'
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / 'somedir'
    real_link = os.readlink(str(built_symlink))
    assert real_link == 'somedir'

    # as a sanity check, the file inside the linked dir should exist
    assert (build_dir / 'thelink' / 'sanity check').exists()


def test_build_generics_symlink_deep(tmp_path):
    """Correctly re-links a symlink across deep dirs."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / 'crazycharm.py'
    entrypoint.touch()

    dir1 = tmp_path / 'dir1'
    dir1.mkdir()
    dir2 = tmp_path / 'dir2'
    dir2.mkdir()
    original_target = dir1 / 'file.real'
    original_target.touch()
    the_symlink = dir2 / 'file.link'
    the_symlink.symlink_to(original_target)

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    built_symlink = build_dir / 'dir2' / 'file.link'
    assert built_symlink.is_symlink()
    assert built_symlink.resolve() == build_dir / 'dir1' / 'file.real'
    real_link = os.readlink(str(built_symlink))
    assert real_link == '../dir1/file.real'


def test_build_generics_symlink_file_outside(tmp_path, caplog):
    """Ignores (with warning) a symlink pointing a file outside projects dir."""
    caplog.set_level(logging.WARNING)

    project_dir = tmp_path / 'test-project'
    project_dir.mkdir()

    build_dir = project_dir / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / 'crazycharm.py'
    entrypoint.touch()

    outside_project = tmp_path / 'dangerous.txt'
    outside_project.touch()
    the_symlink = project_dir / 'external-file'
    the_symlink.symlink_to(outside_project)

    builder = Builder({
        'from': project_dir,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    assert not (build_dir / 'external-file').exists()
    expected = "Ignoring symlink because targets outside the project: 'external-file'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_symlink_directory_outside(tmp_path, caplog):
    """Ignores (with warning) a symlink pointing a dir outside projects dir."""
    caplog.set_level(logging.WARNING)

    project_dir = tmp_path / 'test-project'
    project_dir.mkdir()

    build_dir = project_dir / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = project_dir / 'crazycharm.py'
    entrypoint.touch()

    outside_project = tmp_path / 'dangerous'
    outside_project.mkdir()
    the_symlink = project_dir / 'external-dir'
    the_symlink.symlink_to(outside_project)

    builder = Builder({
        'from': project_dir,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    assert not (build_dir / 'external-dir').exists()
    expected = "Ignoring symlink because targets outside the project: 'external-dir'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_generics_different_filetype(tmp_path, caplog, monkeypatch):
    """Ignores whatever is not a regular file, symlink or dir."""
    caplog.set_level(logging.DEBUG)

    # change into the tmp path and do everything locally, because otherwise the socket path
    # will be too long for mac os
    monkeypatch.chdir(tmp_path)

    build_dir = pathlib.Path(BUILD_DIRNAME)
    build_dir.mkdir()
    entrypoint = pathlib.Path('crazycharm.py')
    entrypoint.touch()

    # create a socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind('test-socket')

    builder = Builder({
        'from': tmp_path,
        'entrypoint': tmp_path / entrypoint,
        'requirement': [],
    })
    builder.handle_generic_paths()

    assert not (build_dir / 'test-socket').exists()
    expected = "Ignoring file because of type: 'test-socket'"
    assert expected in [rec.message for rec in caplog.records]


def test_build_dispatcher_modern_dispatch_created(tmp_path):
    """The dispatcher script is properly built."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / 'somestuff.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    builder.handle_dispatcher(linked_entrypoint)

    included_dispatcher = build_dir / DISPATCH_FILENAME
    with included_dispatcher.open('rt', encoding='utf8') as fh:
        dispatcher_code = fh.read()
    assert dispatcher_code == DISPATCH_CONTENT.format(entrypoint_relative_path='somestuff.py')


def test_build_dispatcher_modern_dispatch_respected(tmp_path):
    """The already included dispatcher script is left untouched."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    already_present_dispatch = build_dir / DISPATCH_FILENAME
    with already_present_dispatch.open('wb') as fh:
        fh.write(b'abc')

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    builder.handle_dispatcher('whatever')

    with already_present_dispatch.open('rb') as fh:
        assert fh.read() == b'abc'


def test_build_dispatcher_classic_hooks_mandatory_created(tmp_path):
    """The mandatory classic hooks are implemented ok if not present."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    linked_entrypoint = build_dir / 'somestuff.py'
    included_dispatcher = build_dir / DISPATCH_FILENAME

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    with patch('charmcraft.commands.build.MANDATORY_HOOK_NAMES', {'testhook'}):
        builder.handle_dispatcher(linked_entrypoint)

    test_hook = build_dir / 'hooks' / 'testhook'
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    real_link = os.readlink(str(test_hook))
    assert real_link == os.path.join('..', DISPATCH_FILENAME)


def test_build_dispatcher_classic_hooks_mandatory_respected(tmp_path):
    """The already included mandatory classic hooks are left untouched."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    built_hooks_dir = build_dir / 'hooks'
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / 'testhook'
    with test_hook.open('wb') as fh:
        fh.write(b'abc')

    linked_entrypoint = build_dir / 'somestuff.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    with patch('charmcraft.commands.build.MANDATORY_HOOK_NAMES', {'testhook'}):
        builder.handle_dispatcher(linked_entrypoint)

    with test_hook.open('rb') as fh:
        assert fh.read() == b'abc'


def test_build_dispatcher_classic_hooks_linking_charm_replaced(tmp_path, caplog):
    """Hooks that are just a symlink to the entrypoint are replaced."""
    caplog.set_level(logging.DEBUG, logger="charmcraft")

    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # simple source code
    src_dir = build_dir / 'src'
    src_dir.mkdir()
    built_charm_script = src_dir / 'charm.py'
    with built_charm_script.open('wb') as fh:
        fh.write(b'all the magic')

    # a test hook, just a symlink to the charm
    built_hooks_dir = build_dir / 'hooks'
    built_hooks_dir.mkdir()
    test_hook = built_hooks_dir / 'somehook'
    test_hook.symlink_to(built_charm_script)

    included_dispatcher = build_dir / DISPATCH_FILENAME

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    builder.handle_dispatcher(built_charm_script)

    # the test hook is still there and a symlink, but now pointing to the dispatcher
    assert test_hook.is_symlink()
    assert test_hook.resolve() == included_dispatcher
    expected = "Replacing existing hook 'somehook' as it's a symlink to the entrypoint"
    assert expected in [rec.message for rec in caplog.records]


def test_build_dependencies_virtualenv_simple(tmp_path):
    """A virtualenv is created with the specified requirements file."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': ['reqs.txt'],
    })

    with patch('charmcraft.commands.build.polite_exec') as mock:
        mock.return_value = 0
        builder.handle_dependencies()

    envpath = build_dir / VENV_DIRNAME
    assert mock.mock_calls == [
        call(['pip3', 'list']),
        call(['pip3', 'install', '--target={}'.format(envpath), '--requirement=reqs.txt']),
    ]


def test_build_dependencies_needs_system(tmp_path):
    """pip3 is called with --system when pip3 needs it."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': ['reqs'],
    })

    with patch('charmcraft.commands.build._pip_needs_system') as is_bionic:
        is_bionic.return_value = True
        with patch('charmcraft.commands.build.polite_exec') as mock:
            mock.return_value = 0
            builder.handle_dependencies()

    envpath = build_dir / VENV_DIRNAME
    assert mock.mock_calls == [
        call(['pip3', 'list']),
        call(['pip3', 'install', '--target={}'.format(envpath), '--system', '--requirement=reqs']),
    ]


def test_build_dependencies_virtualenv_multiple(tmp_path):
    """A virtualenv is created with multiple requirements files."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': ['reqs1.txt', 'reqs2.txt'],
    })

    with patch('charmcraft.commands.build.polite_exec') as mock:
        mock.return_value = 0
        builder.handle_dependencies()

    envpath = build_dir / VENV_DIRNAME
    assert mock.mock_calls == [
        call(['pip3', 'list']),
        call(['pip3', 'install', '--target={}'.format(envpath),
              '--requirement=reqs1.txt', '--requirement=reqs2.txt']),
    ]


def test_build_dependencies_virtualenv_none(tmp_path):
    """The virtualenv is NOT created if no needed."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })

    with patch('charmcraft.commands.build.polite_exec') as mock:
        builder.handle_dependencies()

    mock.assert_not_called()


def test_build_dependencies_virtualenv_error_basicpip(tmp_path):
    """Process is properly interrupted if using pip fails."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': ['something'],
    })

    with patch('charmcraft.commands.build.polite_exec') as mock:
        mock.return_value = -7
        with pytest.raises(CommandError, match="problems using pip"):
            builder.handle_dependencies()


def test_build_dependencies_virtualenv_error_installing(tmp_path):
    """Process is properly interrupted if virtualenv creation fails."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': ['something'],
    })

    with patch('charmcraft.commands.build.polite_exec') as mock:
        mock.side_effect = [0, -7]
        with pytest.raises(CommandError, match="problems installing dependencies"):
            builder.handle_dependencies()


def test_build_package_tree_structure(tmp_path, monkeypatch):
    """The zip file is properly built internally."""
    # the metadata
    metadata_data = {'name': 'name-from-metadata'}
    metadata_file = tmp_path / 'metadata.yaml'
    with metadata_file.open('wt', encoding='ascii') as fh:
        yaml.dump(metadata_data, fh)

    # create some dirs and files! a couple of files outside, and the dir we'll zip...
    file_outside_1 = tmp_path / 'file_outside_1'
    with file_outside_1.open('wb') as fh:
        fh.write(b'content_out_1')
    file_outside_2 = tmp_path / 'file_outside_2'
    with file_outside_2.open('wb') as fh:
        fh.write(b'content_out_2')
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # ...also outside a dir with a file...
    dir_outside = tmp_path / 'extdir'
    dir_outside.mkdir()
    file_ext = dir_outside / 'file_ext'
    with file_ext.open('wb') as fh:
        fh.write(b'external file')

    # ...then another file inside, and another dir...
    file_inside = to_be_zipped_dir / 'file_inside'
    with file_inside.open('wb') as fh:
        fh.write(b'content_in')
    dir_inside = to_be_zipped_dir / 'somedir'
    dir_inside.mkdir()

    # ...also inside, a link to the external dir...
    dir_linked_inside = to_be_zipped_dir / 'linkeddir'
    dir_linked_inside.symlink_to(dir_outside)

    # ...and finally another real file, and two symlinks
    file_deep_1 = dir_inside / 'file_deep_1'
    with file_deep_1.open('wb') as fh:
        fh.write(b'content_deep')
    file_deep_2 = dir_inside / 'file_deep_2'
    file_deep_2.symlink_to(file_inside)
    file_deep_3 = dir_inside / 'file_deep_3'
    file_deep_3.symlink_to(file_outside_1)

    # zip it
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    zipname = builder.handle_package()

    # check the stuff outside is not in the zip, the stuff inside is zipped (with
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipname)
    assert 'file_outside_1' not in [x.filename for x in zf.infolist()]
    assert 'file_outside_2' not in [x.filename for x in zf.infolist()]
    assert zf.read('file_inside') == b"content_in"
    assert zf.read('somedir/file_deep_1') == b"content_deep"  # own
    assert zf.read('somedir/file_deep_2') == b"content_in"  # from file inside
    assert zf.read('somedir/file_deep_3') == b"content_out_1"  # from file outside 1
    assert zf.read('linkeddir/file_ext') == b"external file"  # from file in the outside linked dir


def test_build_package_name(tmp_path, monkeypatch):
    """The zip file name comes from the metadata."""
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # the metadata
    metadata_data = {'name': 'name-from-metadata'}
    metadata_file = tmp_path / 'metadata.yaml'
    with metadata_file.open('wt', encoding='ascii') as fh:
        yaml.dump(metadata_data, fh)

    # zip it
    monkeypatch.chdir(tmp_path)  # so the zip file is left in the temp dir
    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    zipname = builder.handle_package()

    assert zipname == "name-from-metadata.charm"


def test_builder_without_jujuignore(tmp_path):
    """Without a .jujuignore we still have a default set of ignores"""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    ignore = builder._load_juju_ignore()
    assert ignore.match('/.git', is_dir=True)
    assert ignore.match('/build', is_dir=True)
    assert not ignore.match('myfile.py', is_dir=False)


def test_builder_with_jujuignore(tmp_path):
    """With a .jujuignore we will include additional ignores."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    with (tmp_path / '.jujuignore').open('w', encoding='utf-8') as ignores:
        ignores.write(
            '*.py\n'
            '/h\xef.txt\n'
        )

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    ignore = builder._load_juju_ignore()
    assert ignore.match('/.git', is_dir=True)
    assert ignore.match('/build', is_dir=True)
    assert ignore.match('myfile.py', is_dir=False)
    assert not ignore.match('hi.txt', is_dir=False)
    assert ignore.match('h\xef.txt', is_dir=False)
    assert not ignore.match('myfile.c', is_dir=False)


# --- tests for relativise helper

def test_relativise_sameparent():
    """Two files in the same dir."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("dst.txt")


def test_relativise_src_under():
    """The src is in subdirectory of dst's parent."""
    src = pathlib.Path("/tmp/foo/bar/baz/src.txt")
    dst = pathlib.Path("/tmp/foo/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../dst.txt")


def test_relativise_dst_under():
    """The dst is in subdirectory of src's parent."""
    src = pathlib.Path("/tmp/foo/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("bar/baz/dst.txt")


def test_relativise_different_parents_shallow():
    """Different parents for src and dst, but shallow."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../baz/dst.txt")


def test_relativise_different_parents_deep():
    """Different parents for src and dst, in a deep structure."""
    src = pathlib.Path("/tmp/foo/bar1/bar2/src.txt")
    dst = pathlib.Path("/tmp/foo/baz1/baz2/baz3/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../baz1/baz2/baz3/dst.txt")
