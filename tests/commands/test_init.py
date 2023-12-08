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

from argparse import Namespace

import pydocstyle
import pytest

from charmcraft.commands.init import DEFAULT_PROFILE, PROFILES, InitCommand
from tests.test_infra import get_python_filepaths


def pep257_test(python_filepaths):
    """Helper to check PEP257 (used from this module and from test_init.py to check templates)."""
    to_ignore = {
        "D105",  # Missing docstring in magic method
        "D107",  # Missing docstring in __init__
    }
    to_include = pydocstyle.violations.conventions.pep257 - to_ignore
    errors = list(pydocstyle.check(python_filepaths, select=to_include))

    if errors:
        report = [f"Please fix files as suggested by pydocstyle ({len(errors):d} issues):"]
        report.extend(str(e) for e in errors)
        msg = "\n".join(report)
        pytest.fail(msg, pytrace=False)


def create_namespace(*, name="my-charm", author="J Doe", force=False, profile=DEFAULT_PROFILE):
    """Helper to create a valid namespace."""
    return Namespace(name=name, author=author, force=force, profile=profile)


@pytest.mark.parametrize("profile", list(PROFILES))
def test_init_pep257(tmp_path, config, profile):
    cmd = InitCommand(config)
    cmd.run(create_namespace(profile=profile))
    paths = get_python_filepaths(roots=[str(tmp_path / "src")], python_paths=[])
    pep257_test(paths)
