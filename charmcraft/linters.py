# Copyright 2021 Canonical Ltd.
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

"""Analyze and lint charm structures and files."""

import ast
import os
import pathlib
import shlex
from collections import namedtuple
from typing import List

from charmcraft import config

# type of checker/linter
CheckType = namedtuple("CheckType", "trait warning error")(
    trait="trait", warning="warning", error="error"
)

# result information from each checker/linter
CheckResult = namedtuple("CheckResult", "name result url check_type text")

# generic constant for the common 'unknown' result
UNKNOWN = "unknown"

# shared state between checkers, to reuse analysis results and/or other intermediate information
shared_state = {}


class Language:
    """Check the language used to write the charm.

    Currently only Python is detected, if the following checks are true:

    - the charm has a text dispatch with a python call
    - the charm has a `.py` entry point
    - the entry point file is executable
    """

    check_type = CheckType.trait
    name = "language"
    url = "https://juju.is/docs/sdk/charmcraft-analyze#heading--language"
    text = "The charm is written with Python."

    # different result constants
    Result = namedtuple("Result", "python unknown")(python="python", unknown=UNKNOWN)

    @classmethod
    def run(cls, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        # get the entrypoint from the last useful dispatch line
        dispatch = basedir / "dispatch"
        entrypoint_str = ""
        try:
            with dispatch.open("rt", encoding="utf8") as fh:
                last_line = None
                for line in fh:
                    if line.strip():
                        last_line = line
                if last_line:
                    entrypoint_str = shlex.split(last_line)[-1]
        except (IOError, UnicodeDecodeError):
            return cls.Result.unknown

        entrypoint = basedir / entrypoint_str
        if entrypoint.suffix == ".py" and os.access(entrypoint, os.X_OK):
            return cls.Result.python
        return cls.Result.unknown


class Framework:
    """Check on which framework the charm is based on.

    Currently it detects if the Operator Framework is used, if...

    - the language trait is set to python
    - the charm contains venv/ops
    - the charm imports ops in the entry point.

    ...or the Reactive Framework is used, if the charm...

    - has a metadata.yaml with "name" in it
    - has a reactive/<name>,py file that imports "charms.reactive"
    - has a file inside "wheelhouse" dir whose name starts with "charms.reactive-"
    """

    check_type = CheckType.trait
    name = "framework"
    url = "https://juju.is/docs/sdk/charmcraft-analyze#heading--framework"
    text = "The charm is based on the Operator Framework."

    # different result constants
    Result = namedtuple("Result", "operator reactive unknown")(
        operator="operator", reactive="reactive", unknown=UNKNOWN)

    @classmethod
    def run(cls, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        language_info = shared_state[Language.name]
        if language_info['result'] != Language.Result.python:
            return cls.Result.unknown

        opsdir = basedir / 'venv' / 'ops'
        if not opsdir.exists() or not opsdir.is_dir():
            return cls.Result.unknown

        entrypoint = language_info['entrypoint']
        parsed = ast.parse(entrypoint.read_bytes())
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name == 'ops':
                        return cls.Result.operator
            elif isinstance(node, ast.ImportFrom):
                if node.module.split('.')[0] == 'ops':
                    return cls.Result.operator

        # no import found
        return cls.Result.unknown


# all checkers to run; the order here is important, as some checkers depend on the
# results from others
CHECKERS = [
    Language,
    Framework,
]


def analyze(config: config.Config) -> List[CheckResult]:
    """Run all checkers and linters."""
    fixme
