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
"""Integration tests for the project service."""

import pathlib
import shutil

import pytest
from craft_application import ServiceFactory

from charmcraft.application.main import APP_METADATA
from charmcraft.services import register_services
from charmcraft.services.project import ProjectService

SAMPLE_PROJECTS_DIR = pathlib.Path(__file__).parent / "sample_projects"


@pytest.fixture
def service_factory(project_path: pathlib.Path) -> ServiceFactory:
    """Override the service factory since we're generating our own project file."""
    register_services()
    factory = ServiceFactory(app=APP_METADATA)
    factory.update_kwargs("project", project_dir=project_path)
    return factory


@pytest.fixture
def service(service_factory: ServiceFactory, project_path):
    return service_factory.get("project")


@pytest.fixture(
    params=[pytest.param(path, id=path.name) for path in SAMPLE_PROJECTS_DIR.iterdir()]
)
def project_data_path(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture
def project_path(project_path: pathlib.Path, project_data_path: pathlib.Path):
    shutil.copytree(project_data_path / "project", project_path, dirs_exist_ok=True)
    return project_path


@pytest.mark.filterwarnings("ignore:The 'charmhub' field")
def test_project_renders_with_build_plan(
    in_project_path: pathlib.Path,
    service: ProjectService,
    service_factory: ServiceFactory,
):
    service.configure(platform=None, build_for=None)

    service.get()

    service_factory.get("build_plan").plan()
