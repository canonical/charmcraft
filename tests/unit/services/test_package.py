# Copyright 2023-2024 Canonical Ltd.
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
import sys
import zipfile
from typing import Any

import craft_cli.pytest_plugin
import pytest
import pytest_check
from craft_application import util
from craft_application.models import BuildInfo
from craft_providers.bases import BaseName

from charmcraft import const, models, services
from charmcraft.application.main import APP_METADATA
from charmcraft.models.project import BasesCharm

SIMPLE_BUILD_BASE = models.charmcraft.Base(
    name="ubuntu", channel="22.04", architectures=["arm64"]
)
SIMPLE_MANIFEST = models.Manifest(
    charmcraft_started_at="1970-01-01T00:00:00+00:00",
    bases=[SIMPLE_BUILD_BASE],
)
MANIFEST_WITH_ATTRIBUTE = models.Manifest.model_validate(
    SIMPLE_MANIFEST.marshal()
    | {
        "analysis": {"attributes": [models.Attribute(name="boop", result="success")]},
    }
)


@pytest.fixture
def package_service(fake_path, simple_charm, service_factory, default_build_plan):
    fake_project_dir = fake_path / "project"
    fake_project_dir.mkdir(parents=True)

    service_factory.set_kwargs(
        "lifecycle",
        work_dir=fake_path,
        cache_dir=fake_path / "cache",
        build_plan=[],  # Only okay now because we're not asking the lifecycle service to use the plan.
    )

    return services.PackageService(
        app=APP_METADATA,
        project=simple_charm,
        # The package service doesn't call other services
        services=service_factory,
        project_dir=fake_project_dir,
        build_plan=default_build_plan,
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
def test_get_metadata(package_service, simple_charm: BasesCharm, metadata):
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
        (
            [models.CheckResult("lint", "lint", "lint", models.CheckType.LINT, "")],
            SIMPLE_MANIFEST,
        ),
        (
            [models.CheckResult("boop", "success", "", models.CheckType.ATTRIBUTE, "")],
            MANIFEST_WITH_ATTRIBUTE,
        ),
    ],
)
def test_get_manifest(package_service, simple_charm, lint, expected):
    simple_charm._started_at = datetime.datetime(
        1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

    assert package_service.get_manifest(lint) == expected


def test_do_not_overwrite_metadata_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    fake_path,
    package_service,
    simple_charm,
):
    fake_prime_dir = fake_path / "prime"
    fake_prime_dir.mkdir()
    fake_stage_dir = fake_path / "stage"
    fake_stage_dir.mkdir()
    fake_staged_metadata = fake_stage_dir / const.METADATA_FILENAME
    fake_staged_metadata.touch()
    package_service._project.parts["reactive"] = {"source": "."}

    package_service.write_metadata(fake_prime_dir)

    emitter.assert_debug(
        "'metadata.yaml' generated by charm. Not using original project metadata."
    )


def test_do_not_overwrite_actions_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    fake_path,
    package_service,
    simple_charm,
):
    fake_prime_dir = fake_path / "prime"
    fake_prime_dir.mkdir()
    fake_stage_dir = fake_path / "stage"
    fake_stage_dir.mkdir()
    fake_staged_actions = fake_stage_dir / const.JUJU_ACTIONS_FILENAME
    fake_staged_actions.touch()
    package_service._project.parts["reactive"] = {"source": "."}

    package_service.write_metadata(fake_prime_dir)

    emitter.assert_debug("'actions.yaml' generated by charm. Skipping generation.")


# region Tests for getting bases for manifest.yaml
@pytest.mark.parametrize(
    ("bases", "build_item", "expected"),
    [
        (
            [{"name": "ubuntu", "channel": "20.04"}],
            BuildInfo(
                platform=util.get_host_architecture(),
                build_for=util.get_host_architecture(),
                build_on=util.get_host_architecture(),
                base=BaseName("ubuntu", "20.04"),
            ),
            [
                {
                    "name": "ubuntu",
                    "channel": "20.04",
                    "architectures": [util.get_host_architecture()],
                }
            ],
        ),
        (
            [
                {
                    "build-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": ["riscv64"],
                        }
                    ],
                    "run-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": ["all"],
                        },
                    ],
                },
            ],
            BuildInfo(
                platform="riscv64",
                build_for="riscv64",
                build_on="riscv64",
                base=BaseName("ubuntu", "22.04"),
            ),
            [
                {"name": "ubuntu", "channel": "22.04", "architectures": ["all"]},
            ],
        ),
        (
            [{"name": "centos", "channel": "7"}],
            BuildInfo(
                platform=util.get_host_architecture(),
                build_on=util.get_host_architecture(),
                build_for=util.get_host_architecture(),
                base=BaseName("centos", "7"),
            ),
            [
                {
                    "name": "centos",
                    "channel": "7",
                    "architectures": [util.get_host_architecture()],
                }
            ],
        ),
        pytest.param(
            [
                {"name": "centos", "channel": "7"},
                {
                    "build-on": [{"name": "ubuntu", "channel": "20.04"}],
                    "run-on": [
                        {"name": "ubuntu", "channel": "20.04", "architectures": ["all"]}
                    ],
                },
                {
                    "build-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": ["amd64", "arm64"],
                        }
                    ],
                    "run-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": ["arm64"],
                        }
                    ],
                },
            ],
            BuildInfo(
                platform="amd64",
                build_on="amd64",
                build_for="arm64",
                base=BaseName("ubuntu", "22.04"),
            ),
            [{"name": "ubuntu", "channel": "22.04", "architectures": ["arm64"]}],
            id="cross-compile",
        ),
    ],
)
def test_get_manifest_bases_from_bases(
    fake_path: pathlib.Path,
    package_service: services.PackageService,
    bases: list[dict[str, Any]],
    build_item: BuildInfo,
    expected: list[dict[str, Any]],
):
    charm = models.BasesCharm.model_validate(
        {
            "name": "my-charm",
            "description": "",
            "summary": "",
            "type": "charm",
            "bases": bases,
        }
    )
    package_service._project = charm
    package_service._build_plan = [build_item]

    assert package_service.get_manifest_bases() == [
        models.Base.model_validate(b) for b in expected
    ]


@pytest.mark.parametrize("base", ["ubuntu@22.04", "almalinux@9"])
@pytest.mark.parametrize(
    ("platforms", "selected_platform", "expected_architectures"),
    [
        ({"armhf": None}, "armhf", ["armhf"]),
        (
            {
                "anything": {
                    "build-on": [*const.SUPPORTED_ARCHITECTURES],
                    "build-for": ["all"],
                }
            },
            "anything",
            ["all"],
        ),
        (
            {
                "anything": {
                    "build-on": [*const.SUPPORTED_ARCHITECTURES],
                    "build-for": ["all"],
                },
                "amd64": None,
                "riscy": {
                    "build-on": ["arm64", "ppc64el", "riscv64"],
                    "build-for": ["all"],
                },
            },
            "anything",
            ["all"],
        ),
        ({util.get_host_architecture(): None}, None, [util.get_host_architecture()]),
    ],
)
def test_get_manifest_bases_from_platforms(
    package_service, base, platforms, selected_platform, expected_architectures
):
    charm = models.PlatformCharm.model_validate(
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
