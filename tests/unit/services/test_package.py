# Copyright 2023-2025 Canonical Ltd.
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

import pathlib
import sys
import zipfile
from typing import TYPE_CHECKING, Any, cast

import craft_application
import craft_cli.pytest_plugin
import craft_platforms
import distro
import pytest
import pytest_check
from craft_application import util
from craft_platforms import BuildInfo, DebianArchitecture, DistroBase

from charmcraft import const, models, services
from charmcraft.application.main import APP_METADATA

if TYPE_CHECKING:
    from charmcraft.services.package import PackageService

HOST_BASE = craft_platforms.DistroBase.from_linux_distribution(
    distro.LinuxDistribution()
)

SIMPLE_BUILD_BASE = models.charmcraft.Base(
    name=HOST_BASE.distribution, channel=HOST_BASE.series, architectures=["arm64"]
)
SIMPLE_MANIFEST = models.Manifest(
    charmcraft_started_at="2020-03-14T00:00:00+00:00",
    bases=[SIMPLE_BUILD_BASE],
)
MANIFEST_WITH_ATTRIBUTE = models.Manifest.model_validate(
    SIMPLE_MANIFEST.marshal()
    | {
        "analysis": {"attributes": [models.Attribute(name="boop", result="success")]},
    }
)


pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="The package service always runs in Linux."
)


@pytest.fixture
def package_service(
    fake_path, simple_charm, service_factory: craft_application.ServiceFactory
):
    fake_project_dir = fake_path / "project"
    fake_project_dir.mkdir(parents=True)

    service_factory.update_kwargs(
        "lifecycle",
        work_dir=fake_path,
        cache_dir=fake_path / "cache",
    )

    return service_factory.get("package")


def test_get_metadata(
    package_service, service_factory: craft_application.ServiceFactory
):
    project = service_factory.get("project").get()
    metadata = models.CharmMetadata(
        name=project.name,
        summary=cast(str, project.summary),
        description=cast(str, project.description),
    )

    assert package_service.metadata == metadata


@pytest.mark.parametrize(
    ("build_plan", "expected_name"),
    [
        pytest.param(
            [
                BuildInfo(
                    platform="distro-1-test64",
                    build_on=DebianArchitecture.RISCV64,
                    build_for=DebianArchitecture.RISCV64,
                    build_base=DistroBase("ubuntu", "24.04"),
                )
            ],
            "example-charm_distro-1-test64.charm",
            id="simple",
        ),
        pytest.param(
            [
                BuildInfo(
                    platform="ubuntu@24.04:riscv64",
                    build_on=DebianArchitecture.RISCV64,
                    build_for=DebianArchitecture.RISCV64,
                    build_base=DistroBase("ubuntu", "24.04"),
                )
            ],
            "example-charm_ubuntu@24.04-riscv64.charm",
            id="multi-base",
        ),
    ],
)
def test_get_charm_name(
    monkeypatch: pytest.MonkeyPatch,
    package_service,
    service_factory: craft_application.ServiceFactory,
    build_plan,
    expected_name,
):
    monkeypatch.setattr(service_factory.get("build_plan"), "plan", lambda: build_plan)

    assert package_service.get_charm_name() == expected_name


@pytest.mark.parametrize(
    ("lint", "attributes"),
    [
        ([], {}),
        (
            [models.CheckResult("lint", "lint", "lint", models.CheckType.LINT, "")],
            {},
        ),
        (
            [models.CheckResult("boop", "success", "", models.CheckType.ATTRIBUTE, "")],
            {
                "analysis": {
                    "attributes": [models.Attribute(name="boop", result="success")]
                },
            },
        ),
    ],
)
def test_get_manifest(
    package_service,
    simple_charm,
    lint,
    attributes,
    service_factory: craft_application.ServiceFactory,
):
    build_item = service_factory.get("build_plan").plan()[0]
    service_factory.get("project").get_platforms()
    expected = models.Manifest.model_validate(
        {
            "charmcraft-started-at": "2020-03-14T00:00:00+00:00",
            "bases": [
                models.charmcraft.Base(
                    name=distro.id(),
                    channel=distro.version(),
                    architectures=[build_item.build_for],
                )
            ],
            **attributes,
        }
    )

    assert package_service.get_manifest(lint) == expected


def test_do_not_overwrite_metadata_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    package_service,
    service_factory: craft_application.ServiceFactory,
    simple_charm,
):
    dirs = service_factory.get("lifecycle").project_info.dirs
    stage_dir = dirs.stage_dir
    stage_dir.mkdir(exist_ok=True)
    fake_staged_metadata = stage_dir / const.METADATA_FILENAME
    fake_staged_metadata.touch()
    service_factory.get("project").get().parts["reactive"] = {"source": "."}

    package_service.write_metadata(dirs.prime_dir)

    emitter.assert_debug(
        "'metadata.yaml' generated by charm. Not using original project metadata."
    )


def test_do_not_overwrite_actions_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    package_service,
    service_factory,
    simple_charm,
):
    dirs = service_factory.get("lifecycle").project_info.dirs
    stage_dir = dirs.stage_dir
    stage_dir.mkdir(exist_ok=True)
    fake_staged_metadata = stage_dir / const.JUJU_ACTIONS_FILENAME
    fake_staged_metadata.touch()
    service_factory.get("project").get().parts["reactive"] = {"source": "."}

    package_service.write_metadata(dirs.prime_dir)

    emitter.assert_debug("'actions.yaml' generated by charm. Skipping generation.")


def test_do_not_overwrite_config_yaml(
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    fake_path,
    package_service,
    service_factory: craft_application.ServiceFactory,
    simple_charm,
):
    dirs = service_factory.get("lifecycle").project_info.dirs
    stage_dir = dirs.stage_dir
    stage_dir.mkdir(exist_ok=True)
    fake_staged_metadata = stage_dir / const.JUJU_CONFIG_FILENAME
    fake_staged_metadata.touch()
    service_factory.get("project").get().parts["reactive"] = {"source": "."}

    package_service.write_metadata(dirs.prime_dir)

    emitter.assert_debug("'config.yaml' generated by charm. Skipping generation.")


# region Tests for getting bases for manifest.yaml
@pytest.mark.parametrize(
    ("bases", "build_item", "expected"),
    [
        (
            [{"name": "ubuntu", "channel": "20.04"}],
            BuildInfo(
                platform=craft_platforms.DebianArchitecture.from_host(),
                build_for=craft_platforms.DebianArchitecture.from_host(),
                build_on=craft_platforms.DebianArchitecture.from_host(),
                build_base=DistroBase("ubuntu", "20.04"),
            ),
            [
                {
                    "name": "ubuntu",
                    "channel": "20.04",
                    "architectures": [craft_platforms.DebianArchitecture.from_host()],
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
                build_for=craft_platforms.DebianArchitecture.RISCV64,
                build_on=craft_platforms.DebianArchitecture.RISCV64,
                build_base=DistroBase("ubuntu", "22.04"),
            ),
            [
                {"name": "ubuntu", "channel": "22.04", "architectures": ["all"]},
            ],
        ),
        pytest.param(
            [
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
                build_on=craft_platforms.DebianArchitecture.AMD64,
                build_for=craft_platforms.DebianArchitecture.ARM64,
                build_base=DistroBase("ubuntu", "22.04"),
            ),
            [{"name": "ubuntu", "channel": "22.04", "architectures": ["arm64"]}],
            id="cross-compile",
        ),
    ],
)
def test_get_manifest_bases_from_bases(
    monkeypatch: pytest.MonkeyPatch,
    fake_path: pathlib.Path,
    project_path: pathlib.Path,
    bases: list[dict[str, Any]],
    build_item: BuildInfo,
    expected: list[dict[str, Any]],
):
    with (project_path / "charmcraft.yaml").open("w") as f:
        util.dump_yaml(
            {
                "name": "my-charm",
                "description": "",
                "summary": "",
                "type": "charm",
                "bases": bases,
                "parts": {"my-part": {"plugin": "nil"}},
            },
            stream=f,
        )

    services.register_services()
    service_factory = craft_application.ServiceFactory(app=APP_METADATA)
    service_factory.update_kwargs(
        "project",
        project_dir=project_path,
    )
    package_service = cast("PackageService", service_factory.get("package"))

    charm = models.BasesCharm.model_validate(
        {
            "name": "my-charm",
            "description": "",
            "summary": "",
            "type": "charm",
            "bases": bases,
        }
    )
    monkeypatch.setattr(service_factory.get("project"), "get", lambda: charm)
    monkeypatch.setattr(service_factory.get("build_plan"), "plan", lambda: [build_item])

    assert package_service.get_manifest_bases() == [
        models.Base.model_validate(b) for b in expected
    ]


@pytest.mark.parametrize(
    ("base", "build_base", "platforms", "build_item", "expected"),
    [
        pytest.param(
            "ubuntu@24.04",
            None,
            {"test-platform": {"build-on": ["amd64"], "build-for": ["riscv64"]}},
            BuildInfo(
                platform="test-platform",
                build_on=craft_platforms.DebianArchitecture.AMD64,
                build_for=craft_platforms.DebianArchitecture.RISCV64,
                build_base=DistroBase("not-to-be-used", "100"),
            ),
            models.Base(
                # uses the project base
                name="ubuntu",
                channel="24.04",
                architectures=["riscv64"],
            ),
            id="base-from-project",
        ),
        pytest.param(
            "ubuntu@24.04",
            "ubuntu@devel",
            {"test-platform": {"build-on": ["amd64"], "build-for": ["riscv64"]}},
            BuildInfo(
                platform="test-platform",
                build_on=craft_platforms.DebianArchitecture.AMD64,
                build_for=craft_platforms.DebianArchitecture.RISCV64,
                # the BuildInfo will use the build-base, which shouldn't go in the manifest
                build_base=DistroBase("ubuntu", "devel"),
            ),
            models.Base(
                name="ubuntu",
                channel="24.04",
                architectures=["riscv64"],
            ),
            id="ignore-build-base",
        ),
        pytest.param(
            None,
            None,
            {"ubuntu@24.04:amd64": None},
            BuildInfo(
                platform="ubuntu@24.04:amd64",
                build_on=craft_platforms.DebianArchitecture.AMD64,
                build_for=craft_platforms.DebianArchitecture.AMD64,
                build_base=DistroBase("ubuntu", "24.04"),
            ),
            models.Base(
                name="ubuntu",
                channel="24.04",
                architectures=["amd64"],
            ),
            id="multi-base-shorthand",
        ),
        pytest.param(
            None,
            None,
            {
                "test-platform": {
                    "build-on": ["ubuntu@24.04:amd64"],
                    "build-for": ["ubuntu@24.04:riscv64"],
                }
            },
            BuildInfo(
                platform="test-platform",
                build_on=craft_platforms.DebianArchitecture.AMD64,
                build_for=craft_platforms.DebianArchitecture.RISCV64,
                build_base=DistroBase("ubuntu", "24.04"),
            ),
            models.Base(
                name="ubuntu",
                channel="24.04",
                architectures=["riscv64"],
            ),
            id="multi-base-standard",
        ),
    ],
)
def test_get_manifest_bases_from_platforms(
    monkeypatch: pytest.MonkeyPatch,
    project_path: pathlib.Path,
    base,
    build_base,
    platforms,
    build_item,
    expected,
):
    with (project_path / "charmcraft.yaml").open("w") as f:
        util.dump_yaml(
            {
                "name": "my-charm",
                "description": "",
                "summary": "",
                "type": "charm",
                "base": base,
                "build-base": build_base,
                "platforms": platforms,
                "parts": {"my-part": {"plugin": "nil"}},
            },
            stream=f,
        )
    services.register_services()
    service_factory = craft_application.ServiceFactory(app=APP_METADATA)
    service_factory.update_kwargs(
        "project",
        project_dir=project_path,
    )
    package_service = cast("PackageService", service_factory.get("package"))
    service_factory.get("project").configure(platform=None, build_for=None)
    bases = package_service.get_manifest_bases()

    pytest_check.equal(len(bases), 1)
    actual_base = bases[0]
    pytest_check.equal(expected, actual_base)


def test_get_manifest_bases_from_platforms_invalid(
    project_path, package_service, service_factory
):
    with (project_path / "charmcraft.yaml").open("w") as f:
        util.dump_yaml(
            {
                "name": "my-charm",
                "description": "",
                "summary": "",
                "type": "charm",
                "base": None,
                "build-base": None,
                "platforms": {"amd64": None},
                "parts": {"my-part": {"plugin": "nil"}},
            },
            stream=f,
        )
    service_factory._services = {}
    service_factory.get("project").configure(platform=None, build_for=None)

    with pytest.raises(
        craft_platforms.RequiresBaseError,
        match=r"No base or build-base is declared and no base is declared in the platforms section\.",
    ):
        package_service.get_manifest_bases()


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

    charm_path = package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(charm_path)
    assert sorted(x.filename for x in zf.infolist()) == ["bar/baz.txt", "foo.txt"]
    assert zf.read("foo.txt") == b"123\x00456"
    assert zf.read("bar/baz.txt") == b"mo\xc3\xb1o"


def test_zipbuild_symlink_simple(fake_path, package_service):
    """Symlinks are supported."""
    build_dir = fake_path / "somedir"
    build_dir.mkdir()

    testfile1 = build_dir / "real.txt"
    testfile1.write_bytes(b"123\x00456")
    testfile2 = build_dir / "link.txt"
    testfile2.symlink_to(testfile1)

    charm_path = package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(charm_path)
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt", "real.txt"]
    assert zf.read("real.txt") == b"123\x00456"
    assert zf.read("link.txt") == b"123\x00456"


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

    charm_path = package_service.pack_charm(build_dir, fake_path)

    zf = zipfile.ZipFile(charm_path)
    assert sorted(x.filename for x in zf.infolist()) == ["link.txt"]
    assert zf.read("link.txt") == b"123\x00456"


# endregion
