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

import os
import shlex
from collections import namedtuple

CheckType = namedtuple("CheckType", "trait warning error")(
    trait="trait", warning="warning", error="error"
)


class Language:
    """Check the language used to write the charm.

    Currently only Python is detected, if the following checks are true:

    - the charm has a text dispatch with a python call
    - the charm has a `.py` entry point
    - the entry point file is executable
    """

    check_type = CheckType.trait
    name = "language"
    url = "https://juju.is/docs/sdk/charmcraft-analyze#heading--language"  # FIXME: confirm url
    text = "The charm is written with Python."

    # different result constatns
    PYTHON = "python"
    UNKNOWN = "unknown"

    @classmethod
    def run(cls, basedir):
        """Run the proper verifications."""
        # get the entrypoint from the last useful dispatch line
        dispatch = basedir / "dispatch"
        entrypoint_str = ""
        if dispatch.exists():
            last_line = None
            for line in dispatch.open("rt", encoding="utf8"):
                if line.strip():
                    last_line = line
            if last_line:
                entrypoint_str = shlex.split(last_line)[-1]

        entrypoint = basedir / entrypoint_str
        if entrypoint.suffix == ".py" and os.access(entrypoint, os.X_OK):
            return cls.PYTHON
        return cls.UNKNOWN
