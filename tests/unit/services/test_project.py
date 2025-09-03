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
import re

import craft_platforms
import pytest
import yaml
from craft_cli import CraftError

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
    ("bases", "exc_string"),
    [
        (
            [{"name": "ubuntu", "channel": "24.04"}],
            "'ubuntu@24.04'",
        ),
        (
            [
                {"name": "ubuntu", "channel": "22.04"},
                {"name": "ubuntu", "channel": "24.04"},
            ],
            "'ubuntu@24.04'",
        ),
        (
            [
                {"name": "ubuntu", "channel": "25.10"},
                {"name": "ubuntu", "channel": "24.04"},
            ],
            "'ubuntu@24.04', 'ubuntu@25.10'",
        ),
    ],
)
def test_render_legacy_platforms_error(
    project_path: pathlib.Path, service: ProjectService, bases: list[dict], exc_string
):
    (project_path / "charmcraft.yaml").write_text(
        yaml.safe_dump({"name": "bases-test", "type": "charm", "bases": bases})
    )

    with pytest.raises(
        CraftError,
        match=f"^Not valid for use with the 'bases' key: {re.escape(exc_string)}",
    ):
        service._app_render_legacy_platforms()


@pytest.mark.parametrize(
    ("platforms", "expected"),
    [
        *(
            pytest.param(
                {str(arch): None},
                {str(arch): {"build-on": [str(arch)], "build-for": [str(arch)]}},
                id=f"expand-{arch}",
            )
            for arch in craft_platforms.DebianArchitecture
        ),
        *(
            pytest.param(
                {"anything": {"build-on": [str(arch)], "build-for": ["all"]}},
                {"anything": {"build-on": [str(arch)], "build-for": ["all"]}},
                id=f"on-{arch}-for-all",
            )
            for arch in craft_platforms.DebianArchitecture
        ),
        *(
            pytest.param(
                {"unvectored": {"build-on": str(arch), "build-for": "all"}},
                {"unvectored": {"build-on": [str(arch)], "build-for": ["all"]}},
                id=f"vectorise-{arch}",
            )
            for arch in craft_platforms.DebianArchitecture
        ),
        pytest.param(
            {"ppc64el": {"build-on": ["amd64", "riscv64"]}},
            {"ppc64el": {"build-on": ["amd64", "riscv64"], "build-for": ["ppc64el"]}},
            id="only-build-on-valid-name",
        ),
        pytest.param(
            {"all": {"build-on": "riscv64"}},
            {"all": {"build-on": ["riscv64"], "build-for": ["all"]}},
            id="lazy-all",
        ),
        pytest.param(
            {"s390x": {"build-on": "ppc64el", "build-for": None}},
            {"s390x": {"build-on": ["ppc64el"], "build-for": ["s390x"]}},
            id="null-build-for-valid-name",
        ),
        pytest.param(
            {
                "jammy": {
                    "build-on": ["ubuntu@22.04:amd64"],
                    "build-for": ["ubuntu@22.04:amd64"],
                },
                "ubuntu@24.04:riscv64": None,
            },
            {
                "jammy": {
                    "build-on": ["ubuntu@22.04:amd64"],
                    "build-for": ["ubuntu@22.04:amd64"],
                },
                "ubuntu@24.04:riscv64": {
                    "build-on": ["ubuntu@24.04:riscv64"],
                    "build-for": ["ubuntu@24.04:riscv64"],
                },
            },
            id="multi-platform",
        ),
    ],
)
def test_get_platforms_correct(
    project_path: pathlib.Path, service: ProjectService, platforms, expected
):
    (project_path / "charmcraft.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "platforms-test",
                "type": "charm",
                "summary": "a summary",
                "description": "a description",
                "parts": {"something": {"plugin": "nil"}},
                "platforms": platforms,
            }
        )
    )

    assert service.get_platforms() == expected
    # Check that it renders.
    service.configure(platform=None, build_for=None)
    service.get()
    assert service.get().marshal()["platforms"] == expected
