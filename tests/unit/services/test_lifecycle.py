# Copyright 2023-2024 Canonical Ltd.
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
"""Unit tests for the lifecycle service."""

from unittest import mock

import craft_platforms
import pytest
from craft_cli.pytest_plugin import RecordingEmitter

from charmcraft.services.lifecycle import LifecycleService

HOST_ARCH = craft_platforms.DebianArchitecture.from_host()


@pytest.fixture
def service(service_factory) -> LifecycleService:
    return service_factory.get("lifecycle")


@pytest.mark.parametrize(
    ("plan_build_for", "expected"),
    [
        ("amd64", "amd64"),
        ("arm64", "arm64"),
        ("riscv64", "riscv64"),
        ("all", HOST_ARCH),
        # Test multi-arch charms
        (f"{HOST_ARCH}-foreign", "foreign"),
        (f"foreign-{HOST_ARCH}", "foreign"),
    ],
)
def test_get_build_for_values(
    service: LifecycleService, plan_build_for: str, expected: str, service_factory
):
    service_factory.get("build_plan").plan = mock.Mock(
        return_value=[
            craft_platforms.BuildInfo(
                build_base=craft_platforms.DistroBase("ubuntu", "22.04"),
                platform="something",
                build_on=HOST_ARCH,
                build_for=plan_build_for,  # pyright: ignore[reportArgumentType]
            )
        ]
    )
    assert service._get_build_for() == expected


def test_build_for_warns_on_all(
    service: LifecycleService, emitter: RecordingEmitter, service_factory
):
    service_factory.get("build_plan").plan = mock.Mock(
        return_value=[
            craft_platforms.BuildInfo(
                build_base=craft_platforms.DistroBase("ubuntu", "22.04"),
                platform="something",
                build_on=HOST_ARCH,
                build_for="all",
            )
        ]
    )

    assert service._get_build_for() == HOST_ARCH

    emitter.assert_progress(
        "WARNING: Charmcraft does not validate that charms with architecture 'all' "
        "are fully architecture agnostic.",
        permanent=True,
    )


def test_build_for_warns_on_multi(
    service: LifecycleService, emitter: RecordingEmitter, service_factory
):
    service_factory.get("build_plan").plan = mock.Mock(
        return_value=[
            craft_platforms.BuildInfo(
                build_base=craft_platforms.DistroBase("ubuntu", "22.04"),
                platform="something",
                build_on=HOST_ARCH,
                build_for=f"{HOST_ARCH}-foreign",  # pyright: ignore[reportArgumentType]
            )
        ]
    )

    assert service._get_build_for() == "foreign"

    emitter.assert_progress(
        "WARNING: Charmcraft does not validate that charms with multiple "
        "given architectures are architecture agnostic.",
        permanent=True,
    )
