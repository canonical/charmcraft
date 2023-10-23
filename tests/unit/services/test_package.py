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
import sys
import zipfile

import pytest

from charmcraft import models, services
from charmcraft.application.main import APP_METADATA

SIMPLE_BUILD_BASE = models.charmcraft.Base(name="ubuntu", channel="22.04", architectures=["arm64"])


@pytest.fixture()
def package_service(fake_path, simple_charm):
    fake_project_dir = fake_path / "project"
    fake_project_dir.mkdir(parents=True)
    return services.PackageService(
        app=APP_METADATA,
        project=simple_charm,
        # The package service doesn't call other services
        services=None,  # type: ignore[attr]
        project_dir=fake_project_dir,
        platform="distro-1-test64",
    )


@pytest.mark.parametrize(
    "metadata",
    [
        models.CharmMetadata(
            name="charmy-mccharmface",
            summary="Charmy!",
            description="Very charming!",
        ),
    ],
)
def test_get_metadata(package_service, simple_charm, metadata):
    package_service._project = simple_charm

    assert package_service.metadata == metadata


@pytest.mark.parametrize(
    ("bases", "expected_name"),
    [
        (
            [SIMPLE_BUILD_BASE],
            "charmy-mccharmface_distro-1-test64.charm",
        ),
    ],
)
def test_get_charm_path(fake_path, package_service, bases, expected_name):
    fake_prime_dir = fake_path / "prime"
    charm_path = package_service.get_charm_path(fake_prime_dir)

    assert charm_path == fake_prime_dir / expected_name


# region tests for packing the charm
# These tests are modified from test_zipbuild
def test_pack_charm_simple(fake_path, package_service):
    """Build a bunch of files in the zip."""
    build_dir = fake_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "foo.txt"
    testfile1.write_bytes(b"123\x00456")
    subdir = build_dir / "bar"
    subdir.mkdir()
    testfile2 = subdir / "baz.txt"
    testfile2.write_bytes(b"mo\xc3\xb1o")

    package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(fake_path / "charmy-mccharmface_distro-1-test64.charm")
    assert sorted(x.filename for x in zf.infolist()) == ["bar/baz.txt", "foo.txt"]
    assert zf.read("foo.txt") == b"123\x00456"
    assert zf.read("bar/baz.txt") == b"mo\xc3\xb1o"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_zipbuild_symlink_simple(fake_path, package_service):
    """Symlinks are supported."""
    build_dir = fake_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "real.txt"
    testfile1.write_bytes(b"123\x00456")
    testfile2 = build_dir / "link.txt"
    testfile2.symlink_to(testfile1)

    package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(fake_path / "charmy-mccharmface_distro-1-test64.charm")
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt", "real.txt"]
    assert zf.read("real.txt") == b"123\x00456"
    assert zf.read("link.txt") == b"123\x00456"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_zipbuild_symlink_outside(fake_path, package_service):
    """No matter where the symlink points to."""
    # outside the build dir
    testfile1 = fake_path / "real.txt"
    testfile1.write_bytes(b"123\x00456")

    # inside the build dir
    build_dir = fake_path / "somedir"
    build_dir.mkdir()
    testfile2 = build_dir / "link.txt"
    testfile2.symlink_to(testfile1)

    package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(fake_path / "charmy-mccharmface_distro-1-test64.charm")
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt"]
    assert zf.read("link.txt") == b"123\x00456"


# endregion
