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
import subprocess
import sys
from typing import Any

import distro
import pytest
from craft_application import util

from charmcraft import services
from charmcraft.models import project

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="craft-parts is linux-only")
]


@pytest.fixture
def charm_project(
    basic_charm_dict: dict[str, Any], project_path: pathlib.Path, request
):
    return project.PlatformCharm.unmarshal(
        basic_charm_dict
        | {
            "base": f"{distro.id()}@{distro.version()}",
            "platforms": {util.get_host_architecture(): None},
            "parts": {
                "my-charm": {
                    "plugin": "poetry",
                    "source": str(project_path),
                    "source-type": "local",
                }
            },
        },
    )


@pytest.fixture
def poetry_project(project_path: pathlib.Path) -> None:
    subprocess.run(
        [
            "poetry",
            "init",
            "--name=test-charm",
            f"--directory={project_path}",
            "--no-interaction",
        ],
        check=False,
    )
    source_dir = project_path / "src"
    source_dir.mkdir()
    (source_dir / "charm.py").write_text("# Charm file")


@pytest.mark.usefixtures("poetry_project")
def test_poetry_plugin(
    build_plan,
    service_factory: services.CharmcraftServiceFactory,
    tmp_path: pathlib.Path,
):
    install_path = tmp_path / "parts" / "my-charm" / "install"
    stage_path = tmp_path / "stage"
    service_factory.lifecycle._build_plan = build_plan

    service_factory.lifecycle.run("stage")

    # Check that the part install directory looks correct.
    assert (install_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (install_path / "venv" / "lib").is_dir()

    # Check that the stage directory looks correct.
    assert (stage_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (stage_path / "venv" / "lib").is_dir()
    assert not (stage_path / "venv" / "lib64").is_symlink()
