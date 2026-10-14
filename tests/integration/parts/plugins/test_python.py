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
"""Integration tests for the Charmcraft-specific python plugin."""

import pathlib
import sys
import typing

import craft_application
import pytest

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="craft-parts is linux-only")
]


@pytest.mark.slow
@pytest.mark.parametrize("source_subdir", [None, "charm_dir"])
def test_python_plugin(
    service_factory: craft_application.ServiceFactory,
    project_path: pathlib.Path,
    tmp_path: pathlib.Path,
    source_subdir: str | None,
):
    charm_dir = project_path / source_subdir if source_subdir else project_path
    source_path = charm_dir / "src"
    source_path.mkdir(parents=True)
    (source_path / "charm.py").write_text("# Charm file")
    (charm_dir / "requirements.txt").write_text("distro==1.4.0")

    part_def: dict[str, typing.Any] = {
        "plugin": "python",
        "python-requirements": ["requirements.txt"],
        "source": str(project_path),
        "source-type": "local",
    }
    if source_subdir:
        part_def["source-subdir"] = source_subdir

    service_factory.get("project").get().parts = {"my-charm": part_def}

    install_path = tmp_path / "parts" / "my-charm" / "install"
    stage_path = tmp_path / "stage"

    service_factory.lifecycle.run("stage")

    assert (install_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (install_path / "venv" / "lib").is_dir()
    assert (
        len(
            list(
                (install_path / "venv" / "lib").glob("python*/site-packages/distro.py")
            )
        )
        == 1
    )

    assert (stage_path / "src" / "charm.py").read_text() == "# Charm file"
    assert (stage_path / "venv" / "lib").is_dir()
    assert not (stage_path / "venv" / "lib64").is_symlink()
