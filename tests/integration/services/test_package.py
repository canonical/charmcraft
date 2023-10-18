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
import datetime
import pathlib

import freezegun
import pytest
import pytest_check

from charmcraft import models, services
from charmcraft.application.main import APP_METADATA
from tests.unit import SIMPLE_CHARM


@pytest.fixture()
def package_service(fake_project_dir, service_factory):
    svc = services.PackageService(
        app=APP_METADATA,
        project=SIMPLE_CHARM.copy(deep=True),
        # The package service doesn't call other services
        services=service_factory,  # type: ignore[attr]
        project_dir=fake_project_dir,
        platform="ubuntu-22.04-arm64",
    )
    service_factory.package = svc
    return svc


@pytest.mark.parametrize(
    "project_path", list((pathlib.Path(__file__).parent / "sample_projects").iterdir())
)
@freezegun.freeze_time(datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc))
def test_write_metadata(fs, fake_prime_dir, project_path, package_service):
    fs.add_real_directory(project_path)
    expected_prime_dir = project_path / "prime"

    project = models.CharmcraftProject.from_yaml_file(project_path / "project" / "charmcraft.yaml")
    project._started_at = datetime.datetime.utcnow()
    package_service._project = project

    package_service.write_metadata(fake_prime_dir)

    for file in expected_prime_dir.iterdir():
        pytest_check.equal((fake_prime_dir / file.name).read_text(), file.read_text())
