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

import craft_application
import pytest
from craft_cli import messages, printer

from charmcraft import application, services
from charmcraft.application import commands


@pytest.fixture
def project_path(tmp_path: pathlib.Path):
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def make_service_factory(
    new_path: pathlib.Path,
    fake_project_file,
    project_path,
    monkeypatch: pytest.MonkeyPatch,
):
    state_dir = new_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CRAFT_STATE_DIR", str(state_dir))

    def factory_fn():
        services.register_services()
        factory = craft_application.ServiceFactory(app=application.APP_METADATA)
        factory.update_kwargs("charm_libs", project_dir=project_path)
        factory.update_kwargs(
            "lifecycle",
            work_dir=new_path,
            cache_dir=new_path / "cache",
        )
        factory.update_kwargs("project", project_dir=project_path)
        factory.update_kwargs("provider", work_dir=new_path)
        factory.get("project").configure(platform=None, build_for=None)
        factory.get("state").set(
            "charmcraft",
            "started_at",
            value="2020-03-14T00:00:00+00:00",
            overwrite=True,
        )
        return factory

    return factory_fn


@pytest.fixture
def service_factory(make_service_factory):
    return make_service_factory()


@pytest.fixture
def app_factory(
    monkeypatch: pytest.MonkeyPatch,
    new_path: pathlib.Path,
    make_service_factory,
    fake_project_file,
    tmp_path_factory: pytest.TempPathFactory,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    # Keep the log outside the project dir, otherwise it becomes part of the
    # charm source and invalidates the lifecycle state between runs.
    log_path = tmp_path_factory.mktemp("emitter-log") / "emitter.log"
    monkeypatch.setattr(messages, "TESTMODE", True)
    monkeypatch.setattr(printer, "TESTMODE", True)
    state_dir = new_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CRAFT_STATE_DIR", str(state_dir))

    def factory():
        messages.emit.init(
            messages.EmitterMode.QUIET,
            "test-emitter",
            "Hello world",
            log_filepath=log_path,
        )
        service_factory = make_service_factory()
        app = application.Charmcraft(
            app=application.APP_METADATA, services=service_factory
        )
        app._configure_services(None)
        commands.fill_command_groups(app)
        return app

    return factory


@pytest.fixture
def app(app_factory):
    return app_factory()
