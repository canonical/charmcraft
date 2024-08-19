# Copyright 2023 Canonical Ltd.
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
"""Tests for package service."""
import contextlib
import datetime
import pathlib

import freezegun
import pytest
import pytest_check

import charmcraft
from charmcraft import const, models, services
from charmcraft.application.main import APP_METADATA


@pytest.fixture
def package_service(fake_path, service_factory, default_build_plan):
    fake_project_dir = fake_path
    svc = services.PackageService(
        app=APP_METADATA,
        project=service_factory.project,
        services=service_factory,
        project_dir=fake_project_dir,
        build_plan=default_build_plan,
    )
    service_factory.package = svc
    return svc


@pytest.mark.parametrize(
    "project_path",
    [
        pytest.param(path, id=path.name)
        for path in (pathlib.Path(__file__).parent / "sample_projects").iterdir()
    ],
)
@freezegun.freeze_time(datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc))
def test_write_metadata(monkeypatch, fs, package_service, project_path):
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    with contextlib.suppress(FileExistsError):
        fs.add_real_directory(project_path)
    test_prime_dir = pathlib.Path("/prime")
    fs.create_dir(test_prime_dir)
    expected_prime_dir = project_path / "prime"

    project = models.CharmcraftProject.from_yaml_file(project_path / "project" / "charmcraft.yaml")
    project._started_at = datetime.datetime.now(tz=datetime.timezone.utc)
    package_service._project = project

    package_service.write_metadata(test_prime_dir)

    for file in expected_prime_dir.iterdir():
        pytest_check.equal((test_prime_dir / file.name).read_text(), file.read_text())


@pytest.mark.parametrize(
    "project_path",
    [
        pytest.param(path, id=path.name)
        for path in (pathlib.Path(__file__).parent / "sample_projects").iterdir()
    ],
)
@freezegun.freeze_time(datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc))
def test_overwrite_metadata(monkeypatch, fs, package_service, project_path):
    """Test that the metadata file gets rewritten for a charm.

    Regression test for https://github.com/canonical/charmcraft/issues/1654
    """
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    with contextlib.suppress(FileExistsError):
        fs.add_real_directory(project_path)
    test_prime_dir = pathlib.Path("/prime")
    fs.create_dir(test_prime_dir)
    expected_prime_dir = project_path / "prime"

    project = models.CharmcraftProject.from_yaml_file(project_path / "project" / "charmcraft.yaml")
    project._started_at = datetime.datetime.now(tz=datetime.timezone.utc)
    package_service._project = project

    fs.create_file(test_prime_dir / const.METADATA_FILENAME, contents="INVALID!!")

    package_service.write_metadata(test_prime_dir)

    for file in expected_prime_dir.iterdir():
        pytest_check.equal((test_prime_dir / file.name).read_text(), file.read_text())


@freezegun.freeze_time(datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc))
def test_no_overwrite_reactive_metadata(monkeypatch, fs, package_service):
    """Test that the metadata file doesn't get overwritten for a reactive charm..

    Regression test for https://github.com/canonical/charmcraft/issues/1654
    """
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    project_path = pathlib.Path(__file__).parent / "sample_projects" / "basic-reactive"
    with contextlib.suppress(FileExistsError):
        fs.add_real_directory(project_path)
    test_prime_dir = pathlib.Path("/prime")
    fs.create_dir(test_prime_dir)
    test_stage_dir = pathlib.Path("/stage")
    fs.create_dir(test_stage_dir)
    fs.create_file(test_stage_dir / const.METADATA_FILENAME, contents="INVALID!!")

    project = models.CharmcraftProject.from_yaml_file(project_path / "project" / "charmcraft.yaml")
    project._started_at = datetime.datetime.now(tz=datetime.timezone.utc)
    package_service._project = project

    package_service.write_metadata(test_prime_dir)

    assert not (test_prime_dir / const.METADATA_FILENAME).exists()
