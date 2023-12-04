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
"""Models for linters."""
import enum
from typing import final

from pydantic import dataclasses


# Making this a str subclass makes it JSON serialisable as that string.
# This can be replaced with StrEnum once we can drop support for Python < 3.11
class CheckType(str, enum.Enum):
    """Type of analyzer, either attribute check or linter.

    More documentation: https://juju.is/docs/sdk/charmcraft-analyzers-and-linters.
    """

    ATTRIBUTE = "attribute"
    LINT = "lint"


@final
class LintResult:
    """Check results."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
    IGNORED = "ignored"
    UNKNOWN = "unknown"
    NONAPPLICABLE = "nonapplicable"


class ResultLevel(enum.IntEnum):
    """The level of a lint result."""

    UNKNOWN = -1
    OK = 0
    IGNORED = 1
    WARNING = 2
    ERROR = 3
    FATAL = 4

    @classmethod
    def from_result(cls, result: str) -> "ResultLevel":
        """Convert a linting result string to a ResultLevel."""
        try:
            return cls[result.upper()]
        except KeyError:
            return cls.UNKNOWN

    @property
    def return_code(self) -> int:
        """Get an application return code for this lint level."""
        if self == self.FATAL:
            return 1
        if self == self.ERROR:
            return 2
        if self == self.WARNING:
            return 3
        return 0


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """The result of a single linter check."""

    name: str
    result: str
    url: str
    check_type: CheckType
    text: str

    @property
    def level(self) -> ResultLevel:
        """Get the error level of the result."""
        return ResultLevel.from_result(self.result)

    def __str__(self) -> str:
        if self.result == LintResult.IGNORED or not self.result:
            info = ""
        elif self.result == LintResult.UNKNOWN:
            info = self.text
        else:
            info = f"[{self.result.upper()}] {self.text}".strip()

        if info:
            return f"{self.name}: {info} ({self.url})"
        return f"{self.name}: ({self.url}) {info}"
