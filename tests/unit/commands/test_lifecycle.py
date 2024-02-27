# Copyright 2024 Canonical Ltd.
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
"""Unit tests for lifecycle commands."""
import argparse
import sys

from charmcraft.application.commands import lifecycle


def test_pack_run_managed_bundle_by_os(monkeypatch, new_path):
    """When packing a bundle, run_managed should return False if and only if we're on posix."""
    (new_path / "charmcraft.yaml").write_text("type: bundle")

    pack = lifecycle.PackCommand(None)

    result = pack.run_managed(argparse.Namespace())

    if sys.platform in ("win32",):  # non-posix platforms
        assert result, "Didn't ask for managed mode on non-posix platform"
    else:
        assert not result
