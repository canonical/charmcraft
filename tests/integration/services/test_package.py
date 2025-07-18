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

import charmcraft
from charmcraft import const
from charmcraft.application.main import APP_METADATA
from charmcraft.services.package import PackageService


@pytest.fixture(
    params=[
        pytest.param(path, id=path.name)
        for path in (pathlib.Path(__file__).parent / "sample_projects").iterdir()
    ]
)
def project_path(request: pytest.FixtureRequest) -> pathlib.Path:
    return request.param / "project"


@pytest.fixture
def fake_project_yaml(project_path: pathlib.Path) -> str:
    return (project_path / "charmcraft.yaml").read_text()


@pytest.fixture
def package_service(
    project_path: pathlib.Path,
    service_factory,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(project_path)
    svc = PackageService(
        app=APP_METADATA,
        services=service_factory,
    )
    service_factory.package = svc
    return svc


@freezegun.freeze_time(
    datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc)
)
def test_write_metadata(monkeypatch, new_path, package_service, project_path):
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    test_prime_dir = new_path / "prime"
    test_prime_dir.mkdir()
    expected_prime_dir = project_path.parent / "prime"

    package_service.write_metadata(test_prime_dir)

    for file in expected_prime_dir.iterdir():
        pytest_check.equal((test_prime_dir / file.name).read_text(), file.read_text())


@freezegun.freeze_time(
    datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc)
)
def test_overwrite_metadata(monkeypatch, new_path, package_service, project_path):
    """Test that the metadata file gets rewritten for a charm.

    Regression test for https://github.com/canonical/charmcraft/issues/1654
    """
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    test_prime_dir = new_path / "prime"
    test_prime_dir.mkdir()
    expected_prime_dir = project_path.parent / "prime"

    (test_prime_dir / const.METADATA_FILENAME).write_text("INVALID!!")

    package_service.write_metadata(test_prime_dir)

    for file in expected_prime_dir.iterdir():
        pytest_check.equal((test_prime_dir / file.name).read_text(), file.read_text())


@pytest.mark.parametrize(
    "project_path",
    [pathlib.Path(__file__).parent / "sample_projects" / "basic-reactive" / "project"],
)
@freezegun.freeze_time(
    datetime.datetime(2020, 3, 14, 0, 0, 0, tzinfo=datetime.timezone.utc)
)
def test_no_overwrite_reactive_metadata(monkeypatch, new_path, package_service):
    """Test that the metadata file doesn't get overwritten for a reactive charm..

    Regression test for https://github.com/canonical/charmcraft/issues/1654
    """
    monkeypatch.setattr(charmcraft, "__version__", "3.0-test-version")
    test_prime_dir = new_path / "prime"
    test_prime_dir.mkdir()
    test_stage_dir = new_path / "stage"
    test_stage_dir.mkdir()
    (test_stage_dir / const.METADATA_FILENAME).write_text("INVALID!!")

    package_service.write_metadata(test_prime_dir)

    assert not (test_prime_dir / const.METADATA_FILENAME).exists()
