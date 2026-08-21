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
"""Integration tests for the Charmcraft-specific poetry plugin."""

import pathlib
import platform
import subprocess
import sys
import typing

import craft_application
import pytest

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="craft-parts is linux-only")
]


@pytest.mark.slow
@pytest.mark.parametrize("source_subdir", [None, "charm_dir"])
def test_poetry_plugin(
    service_factory: craft_application.ServiceFactory,
    project_path: pathlib.Path,
    tmp_path: pathlib.Path,
    source_subdir: str | None,
):
    charm_dir = project_path / source_subdir if source_subdir else project_path
    charm_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "poetry",
            "init",
            "--name=test-charm",
            f"--python={platform.python_version()}",
            f"--directory={charm_dir}",
            "--no-interaction",
        ],
        cwd=charm_dir,
        capture_output=True,
        check=True,
    )
    source_dir = charm_dir / "src"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "charm.py").write_text("# Charm file")

    part_def: dict[str, typing.Any] = {
        "plugin": "poetry",
        "source": str(project_path),
        "source-type": "local",
    }
    if source_subdir:
        part_def["source-subdir"] = source_subdir

    service_factory.get("project").get().parts = {"my-charm": part_def}

    install_path = tmp_path / "parts" / "my-charm" / "install"
    stage_path = tmp_path / "stage"

    service_factory.lifecycle.run("stage")

    # Check that the part install directory looks correct.
    assert (install_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (install_path / "venv" / "lib").is_dir()

    # Check that the stage directory looks correct.
    assert (stage_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (stage_path / "venv" / "lib").is_dir()
    assert not (stage_path / "venv" / "lib64").is_symlink()
