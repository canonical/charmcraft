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
import subprocess
import sys

import pytest
import pytest_check


@pytest.mark.parametrize("command", [
    "pack", "clean", "init", "version",
    "login", "logout", "whoami", "register", "register-bundle", "unregister",
    "names", "upload", "revisions", "release", "promote-bundle", "close", "status",
    "create-lib", "publish-lib", "fetch-lib", "list-lib", "resources", "upload-resource"
    "resource-revisions"
])
def test_compare_command_and_legacy_options(command):
    command_help = subprocess.run(
        [sys.executable, "-m", "charmcraft", command, "-h"],
        text=True,
        capture_output=True,
        check=True,
    )
    legacy_help = subprocess.run(
        [sys.executable, "-m", "charmcraft.main", command, "-h"],
        text=True,
        capture_output=True,
        check=True,
    )

    past_options = False
    for line in command_help.stderr:
        if not past_options:
            if line == "Options:\n":
                past_options = True
            continue
        if line == "See also:\n":
            break
        pytest_check.is_in(line, legacy_help)
