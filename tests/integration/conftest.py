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
"""General fixtures for integration tests."""

import pathlib
from typing import Any
from unittest import mock

import craft_platforms
import craft_store
import distro
import pytest
from craft_application import util

from charmcraft import application, services
from charmcraft.application import commands
from charmcraft.models import project


@pytest.fixture
def project_path(tmp_path: pathlib.Path):
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def charm_project(
    basic_charm_dict: dict[str, Any], project_path: pathlib.Path, request
):
    # Workaround for testing across systems. If we're not on Ubuntu, make an Ubuntu 24.04 charm.
    # If we are on Ubuntu, use the current version.
    distro_id = "ubuntu"
    distro_version = distro.version() if craft_platforms.is_ubuntu_like() else "24.04"

    return project.PlatformCharm.unmarshal(
        basic_charm_dict
        | {
            "base": f"{distro_id}@{distro_version}",
            "platforms": {util.get_host_architecture(): None},
        },
    )


@pytest.fixture
def service_factory(
    new_path: pathlib.Path, charm_project, default_build_plan, project_path
):
    factory = services.CharmcraftServiceFactory(app=application.APP_METADATA)
    factory.store.client = mock.Mock(spec_set=craft_store.StoreClient)
    factory.project = charm_project
    factory.set_kwargs(
        "lifecycle",
        work_dir=new_path,
        build_plan=default_build_plan,
        cache_dir="~/.cache",
    )
    return factory


@pytest.fixture
def app(monkeypatch, new_path, service_factory):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)
    app._configure_services(None)
    commands.fill_command_groups(app)

    return app
