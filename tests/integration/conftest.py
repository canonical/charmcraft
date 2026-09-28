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
import pytest

from tests.integration.factories import create_app, create_service_factory


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
    state_dir = new_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CRAFT_STATE_DIR", str(state_dir))
    return create_service_factory(
        project_dir=project_path,
        work_dir=new_path,
    )


@pytest.fixture
def app(
    monkeypatch: pytest.MonkeyPatch,
    new_path: pathlib.Path,
    fake_project_file,
    project_path: pathlib.Path,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    state_dir = new_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CRAFT_STATE_DIR", str(state_dir))
    return create_app(
        project_dir=project_path,
        work_dir=new_path,
    )
