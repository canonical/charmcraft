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
"""CLI-related utilities for Charmcraft."""
import datetime
import enum
import json
import numbers
import sys
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Literal, overload

import tabulate
from craft_cli import emit

from charmcraft.env import is_charmcraft_running_in_managed_mode


class SingleOptionEnsurer:
    """Argparse helper to ensure that the option is specified only once, converting it properly.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('-n', '--number',  type=SingleOptionEnsurer(int), required=True)

    No lower limit is checked, that is verified with required=True in the argparse definition.
    """

    def __init__(self, converter):
        self.converter = converter
        self.count = 0

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        self.count += 1
        if self.count > 1:
            raise ValueError("the option can be specified only once")
        return self.converter(value)


@dataclass(frozen=True)
class ResourceOption:
    """Argparse helper to validate and convert a 'resource' option.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('--resource',  type=ResourceOption())
    """

    name: str | None = None
    revision: int | None = None

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        parts = [x.strip() for x in value.split(":")]
        parts = [p for p in parts if p]
        if len(parts) == 2:
            name, revision = parts
            try:
                revision = int(revision)
            except ValueError:
                pass
            else:
                if revision >= 0:
                    return ResourceOption(name, revision)
        msg = (
            "the resource format must be <name>:<revision> (revision being a non-negative integer)"
        )
        raise ValueError(msg)


@dataclass(frozen=True)
class ChoicesList:
    """Argparse helper to make a list argument from a collection of choices.

    For example, a list of digits might look like:

        parser.add_argument("--digits", type=ChoicesList(string.digits))
    """

    choices: Collection

    def __call__(self, value: str) -> list[str]:
        """Validate and get the chosen list of choices.

        :param value: The list as a comma-separated string from the CLI
        :returns: A list of string values.
        :raises ValueError: if any invalid choices are in the list.
        """
        values = value.split(",")
        invalid_values = set(values) - set(self.choices)
        if invalid_values:
            raise ValueError(f"invalid values: {', '.join(invalid_values)}")
        return values


def confirm_with_user(prompt: str, default: bool = False) -> bool:
    """Query user for yes/no answer.

    If stdin is not a tty, the default value is returned.

    If user returns an empty answer, the default value is returned.

    :returns: True if answer starts with [yY], False if answer starts with [nN],
        otherwise the default.
    """
    if is_charmcraft_running_in_managed_mode():
        raise RuntimeError("confirmation not yet supported in managed-mode")

    if not sys.stdin.isatty():
        return default

    choices = " [Y/n]: " if default else " [y/N]: "

    with emit.pause():
        reply = input(prompt + choices).lower().strip()

    if reply and reply[0] == "y":
        return True
    elif reply and reply[0] == "n":
        return False
    else:
        return default


def humanize_list(items: Iterable[str], conjunction: str) -> str:
    """Format a list into a human-readable string.

    :param items: list to humanize, must not be empty
    :param conjunction: the conjunction used to join the final element to
                        the rest of the list (e.g. 'and').
    """
    if not items:
        raise ValueError("Cannot humanize an empty list.")
    *initials, final = map(repr, sorted(items))
    if not initials:
        return final
    return f"{', '.join(initials)} {conjunction} {final}"


def format_timestamp(dt: datetime.datetime) -> str:
    """Convert a datetime object (with or without timezone) to a string.

    The format is

        <DATE>T<TIME>Z

    Always in UTC.
    """
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(None) is not None:
        # timezone aware
        dtz = dt.astimezone(datetime.timezone.utc)
    else:
        # timezone naive, assume it's UTC
        dtz = dt
    return dtz.strftime("%Y-%m-%dT%H:%M:%SZ")


class OutputFormat(enum.Enum):
    """Output format options for commands."""

    DEFAULT = None
    JSON = "json"
    TABLE = "table"


@overload
def format_content(content: dict[str, str], fmt: Literal[OutputFormat.TABLE, "table"]) -> str: ...


@overload
def format_content(
    content: str | (numbers.Real | (list | dict)), fmt: OutputFormat | (str | None)
) -> str: ...


def format_content(content, fmt=None):
    """Format command output."""
    if not isinstance(fmt, OutputFormat):
        try:
            fmt = OutputFormat(fmt)
        except ValueError:
            raise ValueError(f"Unknown output format {str(fmt)}")

    if fmt == OutputFormat.JSON:
        return json.dumps(content, indent=4)
    if fmt == OutputFormat.TABLE:
        return tabulate.tabulate(content, headers="keys")
    return str(content)
