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


import pathlib
from unittest import mock
from craft_parts import lifecycle_manager
import distro
import pytest
from craft_application import errors, models, util
from craft_providers import bases

from charmcraft.services import CharmcraftServiceFactory


def test_init_lifecycle(service_factory: CharmcraftServiceFactory):
    """Test the setup of a parts lifecycle, implicitly testing setup."""

    service_factory.lifecycle._init_lifecycle_manager()


def test_lifecycle_build_for_invalid(service_factory: CharmcraftServiceFactory):
    lifecycle = service_factory.lifecycle

    lifecycle._build_plan = [
        models.BuildInfo(
            platform="something",
            build_on=util.get_host_architecture(),
            build_for="invalid",
            base=bases.BaseName(distro.id(), distro.version()),
        )
    ]

    with pytest.raises(
        errors.PartsLifecycleError, match="[Aa]rchitecture '[a-z]+' is not supported"
    ):
        lifecycle._init_lifecycle_manager()


def test_lifecycle_build_for_all(service_factory: CharmcraftServiceFactory):
    lifecycle = service_factory.lifecycle

    lifecycle._build_plan = [
        models.BuildInfo(
            platform="something",
            build_on=util.get_host_architecture(),
            build_for="all",
            base=bases.BaseName(distro.id(), distro.version()),
        )
    ]

    lcm = lifecycle._init_lifecycle_manager()

    assert lcm._target_arch == util.get_host_architecture()


def test_lifecycle_build_for_multi(service_factory: CharmcraftServiceFactory):
    lifecycle = service_factory.lifecycle

    host_arch = util.get_host_architecture()
    arches = {"arm64", "riscv64", "amd64"} - {host_arch}
    foreign_arch = next(iter(arches))

    lifecycle._build_plan = [
        models.BuildInfo(
            platform="something",
            build_on=util.get_host_architecture(),
            build_for=f"{foreign_arch}-{host_arch}",
            base=bases.BaseName(distro.id(), distro.version()),
        )
    ]

    lcm = lifecycle._init_lifecycle_manager()

    assert lcm._target_arch == foreign_arch


@pytest.mark.skipif(
    distro.id() != "ubuntu", reason="Only valid on Ubuntu"
)
def test_lifecycle_correct_stage_packages(new_path: pathlib.Path, service_factory: CharmcraftServiceFactory, simple_charm):
    simple_charm.parts = {"stage": {"plugin": "nil", "stage-packages": ["curl"]}}
    service_factory.set_kwargs(
        "lifecycle",
        project=simple_charm,
        work_dir=new_path,
        cache_dir=new_path,
        build_plan=[models.BuildInfo(
            platform="something",
            build_on=util.get_host_architecture(),
            build_for=util.get_host_architecture(),
            base=bases.BaseName(distro.id(), distro.version()),
        )],
    )
    lifecycle = service_factory.lifecycle

    # Pretend the build plan is always valid.
    with mock.patch("craft_application.services.lifecycle._validate_build_plan"):
        lifecycle.run("stage")

    doc_dir = new_path / "stage/usr/share/doc"
    # We should only need to stage the curl package, as all other packages are
    # included in the filter list.
    dir_names = [
        package.name
        for package in doc_dir.iterdir()
        if package.is_dir
    ]

    assert dir_names == ["curl"]
