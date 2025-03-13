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
"""Unit tests for the Charmcraft project service."""

from typing import Any

import pytest
from craft_application import ProjectService, util


@pytest.mark.parametrize(
    ("raw_file", "expected"),
    [
        pytest.param(
            {"type": "bundle"},
            {
                "bundle": {
                    "build-on": ["amd64", "arm64", "ppc64el", "riscv64", "s390x"],
                    "build-for": ["all"],
                }
            },
            id="default-bundle",
        ),
        pytest.param(
            {"bases": [{"name": "simple", "channel": "0.0"}]},
            {
                f"simple-0.0-{util.get_host_architecture()}": {
                    "build-on": [f"simple@0.0:{util.get_host_architecture()}"],
                    "build-for": [f"simple@0.0:{util.get_host_architecture()}"],
                    "bases-index": 0,
                }
            },
            id="simple-host-arch",
        ),
        pytest.param(
            {
                "bases": [
                    {
                        "build-on": [{"name": "ubuntu", "channel": "22.04"}],
                        "run-on": [{"name": "ubuntu", "channel": "22.04"}],
                    }
                ],
            },
            {
                f"ubuntu-22.04-{util.get_host_architecture()}": {
                    "build-on": [f"ubuntu@22.04:{util.get_host_architecture()}"],
                    "build-for": [f"ubuntu@22.04:{util.get_host_architecture()}"],
                    "bases-index": 0,
                }
            },
            id="jammy-host-arch",
        ),
        pytest.param(
            {
                "bases": [
                    {"name": "ubuntu", "channel": "20.04", "architectures": ["amd64"]},
                    {"name": "ubuntu", "channel": "22.04", "architectures": ["amd64"]},
                    {"name": "ubuntu", "channel": "22.04", "architectures": ["arm64"]},
                ]
            },
            {
                "ubuntu-20.04-amd64": {
                    "build-on": ["ubuntu@20.04:amd64"],
                    "build-for": ["ubuntu@20.04:amd64"],
                    "bases-index": 0,
                },
                "ubuntu-22.04-amd64": {
                    "build-on": ["ubuntu@22.04:amd64"],
                    "build-for": ["ubuntu@22.04:amd64"],
                    "bases-index": 1,
                },
                "ubuntu-22.04-arm64": {
                    "build-on": ["ubuntu@22.04:arm64"],
                    "build-for": ["ubuntu@22.04:arm64"],
                    "bases-index": 2,
                },
            },
            id="arch-specific-base-specific",
        ),
        pytest.param(
            {
                "bases": [
                    {
                        "name": "ubuntu",
                        "channel": "22.04",
                        "architectures": ["amd64", "arm64"],
                    }
                ]
            },
            {
                "ubuntu-22.04-amd64-arm64": {
                    "build-on": ["ubuntu@22.04:amd64", "ubuntu@22.04:arm64"],
                    "build-for": ["ubuntu@22.04:amd64", "ubuntu@22.04:arm64"],
                    "bases-index": 0,
                }
            },
            id="build-and-run-multi-arch",
        ),
        pytest.param(
            {
                "bases": [
                    {
                        "build-on": [
                            {
                                "name": "ubuntu",
                                "channel": "20.04",
                                "architectures": ["amd64"],
                            }
                        ],
                        "run-on": [
                            {
                                "name": "ubuntu",
                                "channel": "20.04",
                                "architectures": ["amd64"],
                            },
                            {
                                "name": "ubuntu",
                                "channel": "22.04",
                                "architectures": ["amd64"],
                            },
                        ],
                    },
                ],
            },
            {
                "ubuntu-20.04-amd64_ubuntu-22.04-amd64": {
                    "build-on": ["ubuntu@20.04:amd64"],
                    "build-for": ["ubuntu@20.04:amd64", "ubuntu@22.04:amd64"],
                    "bases-index": 0,
                }
            },
            id="run-multi-base",
        ),
    ],
)
def test_render_legacy_platforms(
    project_service: ProjectService, raw_file: dict[str, Any], expected
):
    project_service._load_raw_project = lambda: raw_file  # type: ignore[reportAttributeAccessIssue]

    assert project_service.get_platforms() == expected
