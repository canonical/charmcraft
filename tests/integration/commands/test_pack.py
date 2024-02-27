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
"""Integration tests for packing."""
import textwrap
import zipfile

import pytest

from charmcraft.application import main


@pytest.mark.parametrize(
    "bundle_yaml",
    [
        textwrap.dedent(
            """\
            name: my-bundle
            """
        )
    ],
)
def test_build_basic_bundle(monkeypatch, capsys, new_path, bundle_yaml):
    (new_path / "charmcraft.yaml").write_text("type: bundle")
    (new_path / "bundle.yaml").write_text(bundle_yaml)

    monkeypatch.setattr("sys.argv", ["charmcraft", "pack", f"--project-dir={new_path}"])

    exit_code = main()

    if exit_code != 0:
        stdout, stderr = capsys.readouterr()
        raise ValueError(stdout, stderr)

    with zipfile.ZipFile("bundle.zip") as bundle_zip:
        actual_bundle_yaml = bundle_zip.read("bundle.yaml").decode()

    assert actual_bundle_yaml == bundle_yaml
