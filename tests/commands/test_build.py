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
import os
import sys
import zipfile
from collections import namedtuple
from unittest.mock import patch, call

import pytest
import yaml

from charmcraft.cmdbase import CommandError
from charmcraft.commands import build
from charmcraft.commands.build import (
    BUILD_DIRNAME,
    Builder,
    CHARM_METADATA,
    DISPATCH_CONTENT,
    DISPATCH_FILENAME,
    VENV_DIRNAME,
    Validator,
    polite_exec,
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
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5
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

    dir2 = pathlib.Path(str(dir2))  # comparisons below don't work well in Py3.5
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
    expected_msg = "the charm directory was not found: '/not_really_there'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(pathlib.Path('/not_really_there'))


def test_validator_from_isdir(tmp_path):
    """'from' param: checks that the directory is really that."""
    testfile = tmp_path / 'testfile'
    testfile.touch()

    validator = Validator()
    expected_msg = "the charm directory is not really a directory: '{}'".format(testfile)
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_from(testfile)


def test_validator_entrypoint_simple(tmp_path):
    """'entrypoint' param: simple validation."""
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5
    testfile = tmp_path / 'testfile'
    testfile.touch(mode=0o777)

    validator = Validator()
    resp = validator.validate_entrypoint(testfile)
    assert resp == testfile


def test_validator_entrypoint_default(tmp_path):
    """'entrypoint' param: default value."""
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5
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
    resp = validator.validate_entrypoint(pathlib.Path('dirX/file.py'))
    testfile = pathlib.Path(str(testfile))  # comparison below don't work well in Py3.5
    assert resp == testfile


def test_validator_entrypoint_expanded(tmp_path):
    """'entrypoint' param: expands the user-home prefix."""
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5

    fake_home = tmp_path / 'homedir'
    fake_home.mkdir()

    testfile = fake_home / 'testfile'
    testfile.touch(mode=0o777)

    validator = Validator()

    with patch.dict(os.environ, {'HOME': str(fake_home)}):
        resp = validator.validate_entrypoint(pathlib.Path('~/testfile'))
    assert resp == testfile


def test_validator_entrypoint_exist():
    """'entrypoint' param: checks that the file exists."""
    validator = Validator()
    expected_msg = "the charm entry point was not found: '/not_really_there.py'"
    with pytest.raises(CommandError, match=expected_msg):
        validator.validate_entrypoint(pathlib.Path('/not_really_there.py'))


def test_validator_entrypoint_exec(tmp_path):
    """'entrypoint' param: checks that the file is executable."""
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5
    testfile = tmp_path / 'testfile'
    testfile.touch(mode=0o444)

    validator = Validator()
    expected_msg = "the charm entry point must be executable: '{}'".format(testfile)
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
    testfile = pathlib.Path(str(testfile))  # comparison below don't work well in Py3.5
    assert resp == [testfile]


def test_validator_requirement_expanded(tmp_path):
    """'requirement' param: expands the user-home prefix."""
    tmp_path = pathlib.Path(str(tmp_path))  # comparisons below don't work well in Py3.5

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
        'from': pathlib.Path(str(tmp_path)),  # bad support for tmp_path's pathlib2 in Py3.5
        'entrypoint': pathlib.Path(str(charm_script)),
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


def test_build_code_simple(tmp_path):
    """Check transferred metadata and simple entrypoint."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    metadata = tmp_path / CHARM_METADATA
    entrypoint = tmp_path / 'crazycharm.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    linked_entrypoint = builder.handle_code()

    built_metadata = build_dir / CHARM_METADATA
    assert built_metadata.is_symlink()
    assert built_metadata.resolve() == metadata

    built_entrypoint = build_dir / 'crazycharm.py'
    assert built_entrypoint.is_symlink()
    assert built_entrypoint.resolve() == entrypoint

    assert linked_entrypoint == built_entrypoint


@pytest.mark.parametrize("optional", ["", "config", "actions", "config,actions"])
def test_build_code_optional(tmp_path, optional):
    """Check transferred 'optional' files."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / 'charm.py'

    config = tmp_path / 'config.yaml'
    actions = tmp_path / 'actions.yaml'
    if 'config' in optional:
        config.touch()
    if 'actions' in optional:
        actions.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_code()

    built_config = build_dir / 'config.yaml'
    built_actions = build_dir / 'actions.yaml'

    if 'config' in optional:
        assert built_config.is_symlink()
        assert built_config.resolve() == config
    else:
        assert not built_config.exists()
    if 'actions' in optional:
        assert built_actions.is_symlink()
        assert built_actions.resolve() == actions
    else:
        assert not built_actions.exists()


def test_build_code_optional_bogus(tmp_path, monkeypatch):
    """Check that CHARM_OPTIONAL controls what gets copied."""
    monkeypatch.setattr(build, 'CHARM_OPTIONAL', ['foo.yaml'])

    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()
    entrypoint = tmp_path / 'charm.py'

    config = tmp_path / 'config.yaml'
    config.touch()
    foo = tmp_path / 'foo.yaml'
    foo.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    builder.handle_code()

    built_config = build_dir / 'config.yaml'
    built_foo = build_dir / 'foo.yaml'

    # config.yaml is not in the build
    assert not built_config.exists()
    # but foo.yaml is
    assert built_foo.is_symlink()
    assert built_foo.resolve() == foo


def test_build_code_tree(tmp_path):
    """The whole source code tree is built if entrypoint not at root."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    src_dir = tmp_path / 'code_source'
    entrypoint = src_dir / 'crazycharm.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': entrypoint,
        'requirement': [],
    })
    linked_entrypoint = builder.handle_code()

    built_src = build_dir / 'code_source'
    assert built_src.is_symlink()
    assert built_src.resolve() == src_dir

    assert linked_entrypoint == build_dir / 'code_source' / 'crazycharm.py'


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
    """The already present dispatcher script is properly transferred."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    already_present_dispatch = tmp_path / DISPATCH_FILENAME
    already_present_dispatch.touch()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    builder.handle_dispatcher('whatever')

    included_dispatcher = build_dir / DISPATCH_FILENAME
    assert included_dispatcher.is_symlink()
    assert included_dispatcher.resolve() == already_present_dispatch


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


def test_build_dispatcher_classic_hooks_mandatory_respected(tmp_path):
    """The already present mandatory classic hooks are properly transferred."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    charm_hooks_dir = tmp_path / 'hooks'
    charm_hooks_dir.mkdir()
    charm_test_hook = charm_hooks_dir / 'testhook'
    charm_test_hook.touch()

    linked_entrypoint = build_dir / 'somestuff.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    with patch('charmcraft.commands.build.MANDATORY_HOOK_NAMES', {'testhook'}):
        builder.handle_dispatcher(linked_entrypoint)

    test_hook = build_dir / 'hooks' / 'testhook'
    assert test_hook.is_symlink()
    assert test_hook.resolve() == charm_test_hook


def test_build_dispatcher_classic_hooks_whatever_respected(tmp_path):
    """Any already present stuff in hooks is respected."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    charm_hooks_dir = tmp_path / 'hooks'
    charm_hooks_dir.mkdir()
    charm_test_extra_stuff = charm_hooks_dir / 'extra-stuff'
    charm_test_extra_stuff.touch()

    linked_entrypoint = build_dir / 'somestuff.py'

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    with patch('charmcraft.commands.build.MANDATORY_HOOK_NAMES', {'testhook'}):  # no 'extra-stuff'
        builder.handle_dispatcher(linked_entrypoint)

    test_stuff = build_dir / 'hooks' / 'extra-stuff'
    assert test_stuff.is_symlink()
    assert test_stuff.resolve() == charm_test_extra_stuff


def test_build_dependencies_copied_dirs(tmp_path):
    """The libs with dependencies are properly transferred."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    mod_dir = tmp_path / 'mod'
    mod_dir.mkdir()
    lib_dir = tmp_path / 'lib'
    lib_dir.mkdir()

    builder = Builder({
        'from': tmp_path,
        'entrypoint': 'whatever',
        'requirement': [],
    })
    builder.handle_dependencies()

    # check symlinks were created for those
    built_mod_dir = build_dir / 'mod'
    assert built_mod_dir.is_symlink()
    assert built_mod_dir.resolve() == mod_dir
    built_lib_dir = build_dir / 'lib'
    assert built_lib_dir.is_symlink()
    assert built_lib_dir.resolve() == lib_dir


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
        'from': pathlib.Path(str(tmp_path)),  # bad support for tmp_path's pathlib2 in Py3.5
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
        'from': pathlib.Path(str(tmp_path)),  # bad support for tmp_path's pathlib2 in Py3.5
        'entrypoint': 'whatever',
        'requirement': [],
    })
    zipname = builder.handle_package()

    assert zipname == "name-from-metadata.charm"
