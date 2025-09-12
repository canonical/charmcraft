# Copyright 2020-2022,2025 Canonical Ltd.
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
import re
from pathlib import Path

import pytest

# A list of bash file globs to not check for
IGNORE_GLOBS = frozenset({"tests/spread/**/*.py"})


def get_python_filepaths() -> list[str]:
    """Helper to retrieve paths of Python files."""
    # list of directories to scan
    source_dirs = ["charmcraft", "tests"]
    # list of source files
    source_files = []

    # Parse the globs into their matching files
    cwd = Path.cwd()
    ignore_files: list[Path] = []
    for glob in IGNORE_GLOBS:
        ignore_files.extend(cwd.glob(glob))

    for source_dir in source_dirs:
        # Loop over the source_dir recursively
        # This is done instead of os.walk() to take advantage of Path.resolve()
        for file in Path(source_dir).resolve().glob("**/*.py"):
            if file in ignore_files:
                continue

            source_files.append(str(file))

    return source_files


def test_ensure_copyright() -> None:
    """Check that all non-empty Python files have copyright somewhere in the first 5 lines."""
    issues = []
    regex = re.compile(r"# Copyright \d{4}([-,]\d{4})* Canonical Ltd.$")
    for filepath in get_python_filepaths():
        if Path(filepath).stat().st_size == 0:
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
        msg = "Please add copyright headers to the following files:\n" + "\n".join(
            issues
        )
        pytest.fail(msg, pytrace=False)
