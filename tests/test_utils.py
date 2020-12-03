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

from charmcraft.utils import make_executable, load_yaml


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
