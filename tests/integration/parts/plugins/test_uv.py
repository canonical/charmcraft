import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import distro
import pytest
from craft_application import util as app_util

from charmcraft import services
from charmcraft.models import project

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="craft-parts is linux-only")
]


@pytest.fixture
def charm_project(basic_charm_dict: dict[str, Any], project_path: Path, request):
    return project.PlatformCharm.unmarshal(
        basic_charm_dict
        | {
            "base": f"{distro.id()}@{distro.version()}",
            "platforms": {app_util.get_host_architecture(): None},
            "parts": {
                "my-charm": {
                    "plugin": "uv",
                    "source": str(project_path),
                    "source-type": "local",
                }
            },
        }
    )


@pytest.fixture
def uv_project(project_path: Path) -> None:
    subprocess.run(
        [
            "uv",
            "init",
            "--name=test-charm",
            f"--python={platform.python_version()}",
            "--no-progress",
            str(project_path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "lock",
        ],
        cwd=project_path,
        check=True,
    )
    source_dir = project_path / "src"
    source_dir.mkdir()
    (source_dir / "charm.py").write_text("# Charm file")


@pytest.mark.slow
@pytest.mark.usefixtures("uv_project")
def test_uv_plugin(
    build_plan, service_factory: services.CharmcraftServiceFactory, tmp_path: Path
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
