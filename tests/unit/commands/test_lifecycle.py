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

import pytest

from charmcraft.application.commands import lifecycle


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("linux", False),
        ("macos", True),
        ("win32", True),
    ],
)
def test_pack_run_managed_bundle_by_os(monkeypatch, new_path, platform, expected):
    """When packing a bundle, run_managed should return False if and only if we're on posix."""
    monkeypatch.setattr("sys.platform", platform)
    (new_path / "charmcraft.yaml").write_text("type: bundle")

    pack = lifecycle.PackCommand(None)

    result = pack.run_managed(argparse.Namespace(destructive_mode=False))

    assert result == expected
