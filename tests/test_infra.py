# Copyright 2020-2022 Canonical Ltd.
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

import itertools
import os
import pathlib
import re

import pytest


def get_python_filepaths(*, roots=None, python_paths=None):
    """Helper to retrieve paths of Python files."""
    if python_paths is None:
        python_paths = ["setup.py"]
    if roots is None:
        roots = ["charmcraft", "tests"]
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith(".py"):
                    python_paths.append(os.path.join(dirpath, filename))
    return python_paths


def test_ensure_copyright():
    """Check that all non-empty Python files have copyright somewhere in the first 5 lines."""
    issues = []
    regex = re.compile(r"# Copyright \d{4}(-\d{4})? Canonical Ltd.$")
    for filepath in get_python_filepaths():
        if pathlib.Path(filepath).stat().st_size == 0:
            continue
        if filepath.endswith("charmcraft/_version.py") or filepath.endswith(
            "charmcraft\\_version.py"
        ):
            continue

        with open(filepath, encoding="utf8") as fh:
            for line in itertools.islice(fh, 5):
                if regex.match(line):
                    break
            else:
                issues.append(filepath)
    if issues:
        msg = "Please add copyright headers to the following files:\n" + "\n".join(issues)
        pytest.fail(msg, pytrace=False)
