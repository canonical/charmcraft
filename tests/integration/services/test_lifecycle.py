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
"""Integration tests for the lifecycle service."""

import craft_platforms
import distro
import pytest
from craft_application import ServiceFactory, errors, util


def test_init_lifecycle(service_factory: ServiceFactory):
    """Test the setup of a parts lifecycle, implicitly testing setup."""

    service_factory.get("lifecycle")._init_lifecycle_manager()


def test_lifecycle_build_for_invalid(
    monkeypatch: pytest.MonkeyPatch, service_factory: ServiceFactory
):
    monkeypatch.setattr(
        service_factory.get("build_plan"),
        "plan",
        lambda: [
            craft_platforms.BuildInfo(
                platform="something",
                build_on=craft_platforms.DebianArchitecture.from_host(),
                build_for="invalid",  # pyright: ignore[reportArgumentType]
                build_base=craft_platforms.DistroBase(distro.id(), distro.version()),
            )
        ],
    )

    with pytest.raises(
        errors.PartsLifecycleError, match="[Aa]rchitecture '[a-z]+' is not supported"
    ):
        service_factory.get("lifecycle")


def test_lifecycle_build_for_all(
    monkeypatch: pytest.MonkeyPatch, service_factory: ServiceFactory
):
    monkeypatch.setattr(
        service_factory.get("build_plan"),
        "plan",
        lambda: [
            craft_platforms.BuildInfo(
                platform="something",
                build_on=craft_platforms.DebianArchitecture.from_host(),
                build_for="all",
                build_base=craft_platforms.DistroBase(distro.id(), distro.version()),
            )
        ],
    )
    lifecycle = service_factory.get("lifecycle")

    lcm = lifecycle._init_lifecycle_manager()

    assert lcm._target_arch == util.get_host_architecture()


def test_lifecycle_build_for_multi(
    monkeypatch: pytest.MonkeyPatch, service_factory: ServiceFactory
):
    host_arch = craft_platforms.DebianArchitecture.from_host()
    arches = {"arm64", "riscv64", "amd64"} - {host_arch}
    foreign_arch = next(iter(arches))

    monkeypatch.setattr(
        service_factory.get("build_plan"),
        "plan",
        lambda: [
            craft_platforms.BuildInfo(
                platform="something",
                build_on=host_arch,
                build_for=f"{foreign_arch}-{host_arch}",  # pyright: ignore[reportArgumentType]
                build_base=craft_platforms.DistroBase(distro.id(), distro.version()),
            )
        ],
    )

    lifecycle = service_factory.get("lifecycle")

    lcm = lifecycle._init_lifecycle_manager()

    assert lcm._target_arch == foreign_arch
