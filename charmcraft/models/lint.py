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

from pydantic import dataclasses


class CheckType(str, enum.Enum):
    """Type of analyzer, either attribute check or linter.

    More documentation: https://juju.is/docs/sdk/charmcraft-analyzers-and-linters
    """

    ATTRIBUTE = "attribute"
    LINT = "lint"


class LintResult(enum.Enum):
    """Check results."""

    OK = "ok"
    WARNINGS = "warnings"
    ERRORS = "errors"
    FATAL = "fatal"
    IGNORED = "ignored"
    UNKNOWN = "unknown"
    NONAPPLICABLE = "nonapplicable"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """The result of a single linter check."""

    name: str
    result: str
    url: str
    check_type: CheckType
    text: str
