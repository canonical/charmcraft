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

import datetime
import logging
import os
import pathlib
from textwrap import dedent
from unittest.mock import patch

import pytest
import yaml

from charmcraft import __version__
from charmcraft.cmdbase import CommandError
from charmcraft.utils import (
    ARCH_TRANSLATIONS,
    ResourceOption,
    OSPlatform,
    SingleOptionEnsurer,
    create_manifest,
    get_os_platform,
    load_yaml,
    make_executable,
    useful_filepath,
)


def test_make_executable_read_bits(tmp_path):
    pth = tmp_path / "test"
    pth.touch(mode=0o640)
    # sanity check
    assert pth.stat().st_mode & 0o777 == 0o640
    with pth.open() as fd:
        make_executable(fd)
        # only read bits got made executable
        assert pth.stat().st_mode & 0o777 == 0o750


def test_load_yaml_success(tmp_path):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text("""
        foo: 33
    """)
    content = load_yaml(test_file)
    assert content == {'foo': 33}


def test_load_yaml_no_file(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    test_file = tmp_path / "testfile.yaml"
    content = load_yaml(test_file)
    assert content is None

    expected = "Couldn't find config file {}".format(test_file)
    assert [expected] == [rec.message for rec in caplog.records]


def test_load_yaml_directory(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="charmcraft.commands")

    test_file = tmp_path / "testfile.yaml"
    test_file.mkdir()
    content = load_yaml(test_file)
    assert content is None

    expected = "Couldn't find config file {}".format(test_file)
    assert [expected] == [rec.message for rec in caplog.records]


def test_load_yaml_corrupted_format(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger="charmcraft.commands")

    test_file = tmp_path / "testfile.yaml"
    test_file.write_text("""
        foo: [1, 2
    """)
    content = load_yaml(test_file)
    assert content is None

    (logged,) = [rec.message for rec in caplog.records]
    assert "Failed to read/parse config file {}".format(test_file) in logged
    assert "ParserError" in logged


def test_load_yaml_file_problem(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger="charmcraft.commands")

    test_file = tmp_path / "testfile.yaml"
    test_file.write_text("""
        foo: bar
    """)
    test_file.chmod(0o000)
    content = load_yaml(test_file)
    assert content is None

    (logged,) = [rec.message for rec in caplog.records]
    assert "Failed to read/parse config file {}".format(test_file) in logged
    assert "PermissionError" in logged


# -- tests for the SingleOptionEnsurer helper class

def test_singleoptionensurer_convert_ok():
    """Work fine with one call, convert as expected."""
    soe = SingleOptionEnsurer(int)
    assert soe('33') == 33


def test_singleoptionensurer_too_many():
    """Raise an error after one ok call."""
    soe = SingleOptionEnsurer(int)
    assert soe('33') == 33
    with pytest.raises(ValueError) as cm:
        soe('33')
    assert str(cm.value) == "the option can be specified only once"


# -- tests for the ResourceOption helper class

def test_resourceoption_convert_ok():
    """Convert as expected."""
    r = ResourceOption()("foo:13")
    assert r.name == 'foo'
    assert r.revision == 13


@pytest.mark.parametrize('value', [
    'foo15',  # no separation
    'foo:',  # no revision
    'foo:x3',  # no int
    'foo:0',  # revision 0 is not allowed
    'foo:-1',  # negative revisions are not allowed
    ':15',  # no name
    '  :15',  # no name, really!
    'foo:bar:15',  # invalid name, anyway
])
def test_resourceoption_convert_error(value):
    """Error while converting."""
    with pytest.raises(ValueError) as cm:
        ResourceOption()(value)
    assert str(cm.value) == (
        "the resource format must be <name>:<revision> (revision being a positive integer)")


# -- tests for the useful_filepath helper

def test_usefulfilepath_pathlib(tmp_path):
    """Convert the string to Path."""
    test_file = tmp_path / 'testfile.bin'
    test_file.touch()
    path = useful_filepath(str(test_file))
    assert path == test_file
    assert isinstance(path, pathlib.Path)


def test_usefulfilepath_home_expanded(tmp_path, monkeypatch):
    """Home-expand the indicated path."""
    fake_home = tmp_path / 'homedir'
    fake_home.mkdir()
    test_file = fake_home / 'testfile.bin'
    test_file.touch()

    monkeypatch.setitem(os.environ, 'HOME', str(fake_home))
    path = useful_filepath('~/testfile.bin')
    assert path == test_file


def test_usefulfilepath_missing():
    """The indicated path is not there."""
    with pytest.raises(CommandError) as cm:
        useful_filepath('not_really_there.txt')
    assert str(cm.value) == "Cannot access 'not_really_there.txt'."


def test_usefulfilepath_inaccessible(tmp_path):
    """The indicated path is not readable."""
    test_file = tmp_path / 'testfile.bin'
    test_file.touch(mode=0o000)
    with pytest.raises(CommandError) as cm:
        useful_filepath(str(test_file))
    assert str(cm.value) == "Cannot access {!r}.".format(str(test_file))


def test_usefulfilepath_not_a_file(tmp_path):
    """The indicated path is not a file."""
    with pytest.raises(CommandError) as cm:
        useful_filepath(str(tmp_path))
    assert str(cm.value) == "{!r} is not a file.".format(str(tmp_path))


# -- tests for the OS platform getter

def test_get_os_platform_linux(tmp_path):
    """Utilize an /etc/os-release file to determine platform."""
    # explicitly add commented and empty lines, for parser robustness
    filepath = (tmp_path / "os-release")
    filepath.write_text(dedent(
        """
        # the following is an empty line

        NAME="Ubuntu"
        VERSION="20.04.1 LTS (Focal Fossa)"
        ID=ubuntu
        ID_LIKE=debian
        PRETTY_NAME="Ubuntu 20.04.1 LTS"
        VERSION_ID="20.04"
        HOME_URL="https://www.ubuntu.com/"
        SUPPORT_URL="https://help.ubuntu.com/"
        BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"

        # more in the middle; the following even would be "out of standard", but
        # we should not crash, just ignore it
        SOMETHING-WEIRD

        PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
        VERSION_CODENAME=focal
        UBUNTU_CODENAME=focal
        """
    ))
    with patch('platform.machine', return_value='x86_64'):
        with patch('platform.system', return_value='Linux'):
            os_platform = get_os_platform(filepath)
    assert os_platform.system == "Ubuntu"
    assert os_platform.release == "20.04"
    assert os_platform.machine == "x86_64"


@pytest.mark.parametrize('name', [
    ('"foo bar"', 'foo bar'),  # what's normally found
    ('foo bar', 'foo bar'),  # no quotes
    ('"foo " bar"', 'foo " bar'),  # quotes in the middle
    ('foo bar"', 'foo bar"'),  # unbalanced quotes (no really enclosing)
    ('"foo bar', '"foo bar'),  # unbalanced quotes (no really enclosing)
    ("'foo bar'", 'foo bar'),  # enclosing with single quote
    ("'foo ' bar'", "foo ' bar"),  # single quote in the middle
    ("foo bar'", "foo bar'"),  # unbalanced single quotes (no really enclosing)
    ("'foo bar", "'foo bar"),  # unbalanced single quotes (no really enclosing)
    ("'foo bar\"", "'foo bar\""),  # unbalanced mixed quotes
    ("\"foo bar'", "\"foo bar'"),  # unbalanced mixed quotes
])
def test_get_os_platform_alternative_formats(name, tmp_path):
    """Support different ways of building the string."""
    source, result = name
    filepath = (tmp_path / "os-release")
    filepath.write_text(dedent(
        """
        NAME={}
        VERSION_ID="20.04"
        """.format(source)
    ))
    # need to patch this to "Linux" so actually uses /etc/os-release...
    with patch('platform.system', return_value='Linux'):
        os_platform = get_os_platform(filepath)
    assert os_platform.system == result


def test_get_os_platform_windows():
    """Get platform from a patched Windows machine."""
    with patch('platform.system', return_value='Windows'):
        with patch('platform.release', return_value='10'):
            with patch('platform.machine', return_value='AMD64'):
                os_platform = get_os_platform()
    assert os_platform.system == "Windows"
    assert os_platform.release == "10"
    assert os_platform.machine == "AMD64"


# -- tests for the manifest creation

def test_manifest_simple_ok(tmp_path):
    """Simple construct."""
    tstamp = datetime.datetime(2020, 2, 1, 15, 40, 33)
    os_platform = OSPlatform(system='SuperUbuntu', release='40.10', machine='SomeRISC')
    with patch('charmcraft.utils.get_os_platform', return_value=os_platform):
        result_filepath = create_manifest(tmp_path, tstamp)

    assert result_filepath == tmp_path / 'manifest.yaml'
    saved = yaml.safe_load(result_filepath.read_text())
    expected = {
        'charmcraft-started-at': '2020-02-01T15:40:33Z',
        'charmcraft-version': __version__,
        'bases': [
            {
                'name': 'SuperUbuntu',
                'channel': '40.10',
                'architectures': ['SomeRISC'],
            }
        ],
    }
    assert saved == expected


def test_manifest_architecture_translated(tmp_path, monkeypatch):
    """All known architectures must be translated."""
    monkeypatch.setitem(ARCH_TRANSLATIONS, 'weird_arch', 'nice_arch')
    os_platform = OSPlatform(system='Ubuntu', release='40.10', machine='weird_arch')
    with patch('charmcraft.utils.get_os_platform', return_value=os_platform):
        result_filepath = create_manifest(tmp_path, datetime.datetime.now())

    saved = yaml.safe_load(result_filepath.read_text())
    assert saved['bases'][0]['architectures'] == ['nice_arch']


def test_manifest_dont_overwrite(tmp_path):
    """Don't overwrite the already-existing file."""
    (tmp_path / 'manifest.yaml').touch()
    with pytest.raises(CommandError) as cm:
        create_manifest(tmp_path, datetime.datetime.now())
    assert str(cm.value) == (
        "Cannot write the manifest as there is already a 'manifest.yaml' in disk.")
