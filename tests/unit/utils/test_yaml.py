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
import sys
import textwrap

import pytest

from charmcraft.utils.yaml import dump_yaml, load_yaml


def test_load_yaml_success(tmp_path):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: 33
    """
    )
    content = load_yaml(test_file)
    assert content == {"foo": 33}


def test_load_yaml_no_file(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    content = load_yaml(test_file)
    assert content is None

    expected = f"Couldn't find config file {str(test_file)!r}"
    emitter.assert_debug(expected)


def test_load_yaml_directory(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.mkdir()
    content = load_yaml(test_file)
    assert content is None

    expected = f"Couldn't find config file {str(test_file)!r}"
    emitter.assert_debug(expected)


def test_load_yaml_corrupted_format(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: [1, 2
    """
    )
    content = load_yaml(test_file)
    assert content is None

    expected = "Failed to read/parse config file.*testfile.yaml.*ParserError.*"
    emitter.assert_debug(expected, regex=True)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_load_yaml_file_problem(tmp_path, emitter):
    test_file = tmp_path / "testfile.yaml"
    test_file.write_text(
        """
        foo: bar
    """
    )
    test_file.chmod(0o000)
    content = load_yaml(test_file)
    assert content is None

    expected = f"Failed to read/parse config file {str(test_file)!r}.*PermissionError.*"
    emitter.assert_debug(expected, regex=True)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (None, "null\n...\n"),
        (1, "1\n...\n"),
        ("Stringy!", "Stringy!\n...\n"),
        (
            {"thing": "multi\nline\nstring\n", "single": "single line string"},
            textwrap.dedent(
                """\
            thing: |
              multi
              line
              string
            single: single line string
            """
            ),
        ),
    ],
)
def test_dump_yaml(data, expected):
    assert dump_yaml(data) == expected
