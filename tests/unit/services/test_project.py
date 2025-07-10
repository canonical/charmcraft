# Copyright 2025 Canonical Ltd.
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
"""Unit tests for the charmcraft-specific project service."""

import pathlib

import craft_platforms
import pytest
import yaml

from charmcraft.application.main import APP_METADATA
from charmcraft.services.project import ProjectService

CURRENT_ARCH = craft_platforms.DebianArchitecture.from_host()


@pytest.fixture
def service(project_path):
    return ProjectService(app=APP_METADATA, services=None, project_dir=project_path)


@pytest.mark.parametrize(
    ("bases", "expected"),
    [
        pytest.param(
            [{"name": "ubuntu", "channel": "20.04"}],
            {
                f"ubuntu-20.04-{CURRENT_ARCH}": {
                    "build-on": [f"ubuntu@20.04:{CURRENT_ARCH}"],
                    "build-for": [f"ubuntu@20.04:{CURRENT_ARCH}"],
                },
            },
            id="focal-current-arch",
        ),
        pytest.param(
            [{"name": "ubuntu", "channel": "22.04", "architectures": ["riscv64"]}],
            {
                "ubuntu-22.04-riscv64": {
                    "build-on": ["ubuntu@22.04:riscv64"],
                    "build-for": ["ubuntu@22.04:riscv64"],
                }
            },
            id="jammy-riscv64-no-cross",
        ),
    ],
)
def test_render_legacy_platforms(project_path, service, bases, expected):
    (project_path / "charmcraft.yaml").write_text(
        yaml.safe_dump({"name": "bases-test", "type": "charm", "bases": bases})
    )

    assert service._app_render_legacy_platforms() == expected


@pytest.mark.parametrize(
    "bases",
    [
        [{"name": "ubuntu", "channel": "24.04"}],
    ],
)
def test_render_legacy_platforms_error(
    project_path: pathlib.Path, service: ProjectService, bases: list[dict]
):
    (project_path / "charmcraft.yaml").write_text(
        yaml.safe_dump({"name": "bases-test", "type": "charm", "bases": bases})
    )

    with pytest.raises(ValueError):
        service._app_render_legacy_platforms()
