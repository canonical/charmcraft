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
"""Unit tests for the provider service."""

import pathlib

import pytest
from craft_providers import bases

from charmcraft import models, services


@pytest.fixture
def provider_service(
    fake_path: pathlib.Path,
    service_factory: services.CharmcraftServiceFactory,
    default_build_plan: list[models.CharmBuildInfo],
) -> services.ProviderService:
    fake_cache_dir = fake_path / "cache"
    fake_cache_dir.mkdir(parents=True)

    service_factory.set_kwargs(
        "provider",
        work_dir=fake_path,
        build_plan=default_build_plan,
        provider_name="host",
    )

    return service_factory.provider


@pytest.mark.parametrize(
    "base_name",
    [
        bases.BaseName("ubuntu", "20.04"),
        bases.BaseName("ubuntu", "22.04"),
        bases.BaseName("ubuntu", "24.04"),
        bases.BaseName("ubuntu", "devel"),
        pytest.param(
            bases.BaseName("centos", "7"),
            marks=[
                pytest.mark.xfail(
                    raises=AssertionError,
                    strict=True,
                    reason="https://github.com/canonical/craft-providers/issues/608",
                )
            ],
        ),
        bases.BaseName("almalinux", "9"),
    ],
)
def test_get_base_forwards_cache(
    monkeypatch,
    provider_service: services.ProviderService,
    fake_path: pathlib.Path,
    base_name: bases.BaseName,
):
    monkeypatch.setattr("charmcraft.env.get_host_shared_cache_path", lambda: fake_path / "cache")

    base = provider_service.get_base(
        base_name=base_name,
        instance_name="charmcraft-test-instance",
    )

    assert base._cache_path == fake_path / "cache"
