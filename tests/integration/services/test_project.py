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

SAMPLE_PROJECTS_DIR = pathlib.Path(__file__).parent / "sample_projects"


@pytest.fixture(
    params=[pytest.param(path, id=path.name) for path in SAMPLE_PROJECTS_DIR.iterdir()]
)
def project_data_path(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture
def project_path(project_path: pathlib.Path, project_data_path: pathlib.Path):
    shutil.copytree(project_data_path / "project", project_path, dirs_exist_ok=True)
    return project_path


def test_project_renders(project_path, service_factory: ServiceFactory):
    project_service = service_factory.get("project")

    project_service.__raw_project = None

    project_service.configure(platform=None, build_for=None)
    project_service.get()
