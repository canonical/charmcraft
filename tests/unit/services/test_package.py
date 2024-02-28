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
import sys
import zipfile

import craft_cli.pytest_plugin
import pytest
import pytest_check

from charmcraft import const, models, services, utils
from charmcraft.application.main import APP_METADATA

SIMPLE_BUILD_BASE = models.charmcraft.Base(name="ubuntu", channel="22.04", architectures=["arm64"])
SIMPLE_MANIFEST = models.Manifest(
    charmcraft_started_at="1970-01-01T00:00:00+00:00",
    bases=[models.Base(name="ubuntu", channel="22.04", architectures=["arm64"])],
)
MANIFEST_WITH_ATTRIBUTE = models.Manifest(
    **SIMPLE_MANIFEST.marshal(),
    analysis={"attributes": [models.Attribute(name="boop", result="success")]},
)


@pytest.fixture()
def package_service(fake_path, simple_charm, service_factory):
    fake_project_dir = fake_path / "project"
    fake_project_dir.mkdir(parents=True)

    service_factory.set_kwargs(
        "lifecycle",
        work_dir=fake_path,
        cache_dir=fake_path / "cache",
        build_for=None,
        build_plan=[],
    )

    return services.PackageService(
        app=APP_METADATA,
        project=simple_charm,
        # The package service doesn't call other services
        services=service_factory,
        project_dir=fake_project_dir,
        platform="distro-1-test64",
        build_plan=[],
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


@pytest.mark.parametrize(
    ("lint", "expected"),
    [
        ([], SIMPLE_MANIFEST),
        ([models.CheckResult("lint", "lint", "lint", models.CheckType.LINT, "")], SIMPLE_MANIFEST),
        (
            [models.CheckResult("boop", "success", "", models.CheckType.ATTRIBUTE, "")],
            MANIFEST_WITH_ATTRIBUTE,
        ),
    ],
)
def test_get_manifest(package_service, simple_charm, lint, expected):
    simple_charm._started_at = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    assert package_service.get_manifest(lint) == expected


def test_do_not_overwrite_metadata_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter, fake_path, package_service, simple_charm
):
    fake_prime_dir = fake_path / "prime"
    fake_prime_dir.mkdir()
    fake_metadata_yaml = fake_prime_dir / "metadata.yaml"
    fake_metadata_yaml.touch()

    package_service.write_metadata(fake_prime_dir)

    emitter.assert_debug(
        "'metadata.yaml' generated by charm, not using original project metadata."
    )


# region Tests for getting bases for manifest.yaml
@pytest.mark.parametrize(
    ("bases", "expected"),
    [
        (
            [{"name": "ubuntu", "channel": "20.04"}],
            [
                {
                    "name": "ubuntu",
                    "channel": "20.04",
                    "architectures": [utils.get_host_architecture()],
                }
            ],
        ),
        (
            [
                {"name": "ubuntu", "channel": "22.04", "architectures": ["all"]},
                {"name": "ubuntu", "channel": "20.04", "architectures": ["riscv64"]},
            ],
            [
                {"name": "ubuntu", "channel": "22.04", "architectures": ["all"]},
                {"name": "ubuntu", "channel": "20.04", "architectures": ["riscv64"]},
            ],
        ),
    ],
)
def test_get_manifest_bases_from_bases(fake_path, package_service, bases, expected):
    charm = models.BasesCharm.parse_obj(
        {
            "name": "my-charm",
            "description": "",
            "summary": "",
            "type": "charm",
            "bases": [{"build-on": bases, "run-on": bases}],
        }
    )
    package_service._project = charm

    assert package_service.get_manifest_bases() == [models.Base.parse_obj(b) for b in expected]


@pytest.mark.parametrize("base", ["ubuntu@22.04", "ubuntu@24.04", "almalinux@9"])
@pytest.mark.parametrize(
    ("platforms", "selected_platform", "expected_architectures"),
    [
        ({"armhf": None}, "armhf", ["armhf"]),
        (
            {"anything": {"build-on": [*const.SUPPORTED_ARCHITECTURES], "build-for": "all"}},
            "anything",
            ["all"],
        ),
        (
            {
                "anything": {"build-on": [*const.SUPPORTED_ARCHITECTURES], "build-for": "all"},
                "amd64": None,
                "riscy": {"build-on": ["arm64", "ppc64el", "riscv64"], "build-for": ["all"]},
            },
            "anything",
            ["all"],
        ),
        ({utils.get_host_architecture(): None}, None, [utils.get_host_architecture()]),
        ({"invalid-arch": None}, None, [utils.get_host_architecture()]),
    ],
)
def test_get_manifest_bases_from_platforms(
    package_service, base, platforms, selected_platform, expected_architectures
):
    charm = models.PlatformCharm.parse_obj(
        {
            "name": "my-charm",
            "description": "",
            "summary": "",
            "type": "charm",
            "base": base,
            "platforms": platforms,
            "parts": {},
        }
    )
    package_service._project = charm
    package_service._platform = selected_platform

    bases = package_service.get_manifest_bases()

    pytest_check.equal(len(bases), 1)
    actual_base = bases[0]
    pytest_check.equal(f"{actual_base.name}@{actual_base.channel}", base)
    pytest_check.equal(actual_base.architectures, expected_architectures)


# endregion
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
