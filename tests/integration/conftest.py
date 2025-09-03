# Copyright 2024-2025 Canonical Ltd.
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
from unittest import mock

import craft_application
import craft_store
import pytest

from charmcraft import application, services
from charmcraft.application import commands


@pytest.fixture
def project_path(tmp_path: pathlib.Path):
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def service_factory(
    new_path: pathlib.Path,
    fake_project_file,
    project_path,
    monkeypatch: pytest.MonkeyPatch,
):
    services.register_services()
    factory = craft_application.ServiceFactory(app=application.APP_METADATA)
    factory.get("store").client = mock.Mock(spec_set=craft_store.StoreClient)  # pyright: ignore[reportAttributeAccessIssue]
    factory.update_kwargs(
        "charm_libs",
        project_dir=project_path,
    )
    factory.update_kwargs(
        "lifecycle",
        work_dir=new_path,
        cache_dir="~/.cache",
    )
    factory.update_kwargs(
        "project",
        project_dir=project_path,
    )
    factory.update_kwargs(
        "provider",
        work_dir=new_path,
    )
    factory.get("project").configure(
        platform=None,
        build_for=None,
    )
    monkeypatch.setenv("CRAFT_STATE_DIR", str(new_path / "state"))
    factory.get("state").set(
        "charmcraft", "started_at", value="2020-03-14T00:00:00+00:00"
    )
    return factory


@pytest.fixture
def app(monkeypatch, new_path, service_factory):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)
    app._configure_services(None)
    commands.fill_command_groups(app)

    return app
