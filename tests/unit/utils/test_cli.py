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
"""Unit tests for CLI-related utilities."""
import datetime
import json
from unittest.mock import call, patch

import dateutil.parser
import pytest
import tabulate
from hypothesis import given, strategies

from charmcraft.utils.cli import (
    ChoicesList,
    OutputFormat,
    ResourceOption,
    SingleOptionEnsurer,
    confirm_with_user,
    format_content,
    format_timestamp,
    humanize_list,
)

OUTPUT_VALUES_STRATEGY = strategies.one_of(
    strategies.none(), strategies.integers(), strategies.text()
)
BASIC_LISTS_STRATEGY = strategies.lists(OUTPUT_VALUES_STRATEGY)
BASIC_DICTS_STRATEGY = strategies.dictionaries(
    strategies.one_of(OUTPUT_VALUES_STRATEGY), strategies.one_of(OUTPUT_VALUES_STRATEGY)
)
COMPOUND_DICTS_STRATEGY = strategies.dictionaries(
    strategies.one_of(OUTPUT_VALUES_STRATEGY),
    strategies.one_of(OUTPUT_VALUES_STRATEGY, BASIC_DICTS_STRATEGY),
)


@pytest.fixture
def mock_isatty():
    with patch("sys.stdin.isatty", return_value=True) as mock_isatty:
        yield mock_isatty


@pytest.fixture
def mock_input():
    with patch("charmcraft.utils.cli.input", return_value="") as mock_input:
        yield mock_input


@pytest.fixture
def mock_is_charmcraft_running_in_managed_mode():
    with patch(
        "charmcraft.utils.cli.is_charmcraft_running_in_managed_mode", return_value=False
    ) as mock_managed:
        yield mock_managed


def test_singleoptionensurer_convert_ok():
    """Work fine with one call, convert as expected."""
    soe = SingleOptionEnsurer(int)
    assert soe("33") == 33


def test_singleoptionensurer_too_many():
    """Raise an error after one ok call."""
    soe = SingleOptionEnsurer(int)
    assert soe("33") == 33
    with pytest.raises(ValueError) as cm:
        soe("33")
    assert str(cm.value) == "the option can be specified only once"


def test_resourceoption_convert_ok():
    """Convert as expected."""
    r = ResourceOption()("foo:13")
    assert r.name == "foo"
    assert r.revision == 13


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("foo15", id="no separation"),
        pytest.param("foo:", id="no revision"),
        pytest.param("foo:x3", id="non-integer revision"),
        pytest.param("foo:-1", id="negative revisions are not allowed"),
        pytest.param(":15", id="no name"),
        pytest.param("  :15", id="no name, really!"),
        pytest.param("foo:bar:15", id="invalid name"),
    ],
)
def test_resourceoption_convert_error(value):
    """Error while converting."""
    with pytest.raises(ValueError) as cm:
        ResourceOption()(value)
    assert str(cm.value) == (
        "the resource format must be <name>:<revision> (revision being a non-negative integer)"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("abc", ["abc"]),
        ("abc,def", ["abc", "def"]),
    ],
)
def test_choices_list_success(value, expected):
    choices_list = ChoicesList(["abc", "def", "ghi"])

    assert choices_list(value) == expected


def test_choices_list_invalid_values():
    choices_list = ChoicesList({})

    with pytest.raises(ValueError, match="^invalid values: abc$"):
        choices_list("abc")


def test_confirm_with_user_defaults_with_tty(mock_input, mock_isatty):
    mock_input.return_value = ""
    mock_isatty.return_value = True

    assert confirm_with_user("prompt", default=True) is True
    assert mock_input.mock_calls == [call("prompt [Y/n]: ")]
    mock_input.reset_mock()

    assert confirm_with_user("prompt", default=False) is False
    assert mock_input.mock_calls == [call("prompt [y/N]: ")]


def test_confirm_with_user_defaults_without_tty(mock_input, mock_isatty):
    mock_isatty.return_value = False

    assert confirm_with_user("prompt", default=True) is True
    assert confirm_with_user("prompt", default=False) is False

    assert mock_input.mock_calls == []


@pytest.mark.parametrize(
    ("user_input", "expected"),
    [
        ("y", True),
        ("Y", True),
        ("yes", True),
        ("YES", True),
        ("n", False),
        ("N", False),
        ("no", False),
        ("NO", False),
    ],
)
def test_confirm_with_user(user_input, expected, mock_input, mock_isatty):
    mock_input.return_value = user_input

    assert confirm_with_user("prompt") == expected
    assert mock_input.mock_calls == [call("prompt [y/N]: ")]


def test_confirm_with_user_errors_in_managed_mode(mock_is_charmcraft_running_in_managed_mode):
    mock_is_charmcraft_running_in_managed_mode.return_value = True

    with pytest.raises(RuntimeError):
        confirm_with_user("prompt")


def test_confirm_with_user_pause_emitter(mock_isatty, emitter):
    """The emitter should be paused when using the terminal."""
    mock_isatty.return_value = True

    def fake_input(prompt):
        """Check if the Emitter is paused."""
        assert emitter.paused
        return ""

    with patch("charmcraft.utils.cli.input", fake_input):
        confirm_with_user("prompt")


def test_timestampstr_simple():
    """Converts a timestamp without timezone."""
    source = datetime.datetime(2020, 7, 3, 20, 30, 40)
    result = format_timestamp(source)
    assert result == "2020-07-03T20:30:40Z"


def test_timestampstr_utc():
    """Converts a timestamp with UTC timezone."""
    source = dateutil.parser.parse("2020-07-03T20:30:40Z")
    result = format_timestamp(source)
    assert result == "2020-07-03T20:30:40Z"


def test_timestampstr_nonutc():
    """Converts a timestamp with other timezone."""
    source = dateutil.parser.parse("2020-07-03T20:30:40+03:00")
    result = format_timestamp(source)
    assert result == "2020-07-03T17:30:40Z"


@pytest.mark.parametrize(
    ("items", "conjunction", "expected"),
    (
        (["foo"], "xor", "'foo'"),
        (["foo", "bar"], "xor", "'bar' xor 'foo'"),
        (["foo", "bar", "baz"], "xor", "'bar', 'baz' xor 'foo'"),
        (["foo", "bar", "baz", "qux"], "xor", "'bar', 'baz', 'foo' xor 'qux'"),
    ),
)
def test_humanize_list_ok(items, conjunction, expected):
    """Several successful cases."""
    assert humanize_list(items, conjunction) == expected


def test_humanize_list_empty():
    """Calling to humanize an empty list is an error that should be explicit."""
    with pytest.raises(ValueError):
        humanize_list([], "whatever")


@given(
    strategies.one_of(
        strategies.none(),
        strategies.integers(),
        strategies.text(),
        strategies.dates(),
    )
)
def test_format_content_string(content):
    assert format_content(content, None) == str(content)


@given(
    strategies.one_of(
        strategies.none(),
        strategies.integers(),
        strategies.floats(),
        strategies.text(),
        BASIC_LISTS_STRATEGY,
        COMPOUND_DICTS_STRATEGY,
    )
)
def test_format_content_json(content):
    assert format_content(content, "json") == json.dumps(content, indent=4)


@given(
    strategies.lists(
        strategies.fixed_dictionaries(
            {
                "first column": OUTPUT_VALUES_STRATEGY,
                "Column 2": OUTPUT_VALUES_STRATEGY,
                3: OUTPUT_VALUES_STRATEGY,
                None: OUTPUT_VALUES_STRATEGY,
            }
        )
    )
)
def test_format_content_table(content):
    assert format_content(content, OutputFormat.TABLE) == tabulate.tabulate(
        content, headers="keys"
    )


@pytest.mark.parametrize("fmt", ["yolo", 0])
def test_format_content_invalid(fmt):
    with pytest.raises(ValueError, match="^Unknown output format "):
        format_content(None, fmt)
