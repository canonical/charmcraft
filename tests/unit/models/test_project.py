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
"""Unit tests for project-related models."""
import itertools
import json
import pathlib
from textwrap import dedent
from typing import Any

import pydantic
import pyfakefs.fake_filesystem
import pytest
import pytest_check
from craft_application import models
from craft_application.errors import CraftValidationError
from craft_application.util import safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases

from charmcraft import const, utils
from charmcraft.models import project
from charmcraft.models.charmcraft import Base, BasesConfiguration

SIMPLE_BASE = Base(name="simple", channel="0.0")
BASE_WITH_ONE_ARCH = Base(name="arch", channel="1.0", architectures=["amd64"])
BASE_WITH_MULTIARCH = Base(name="multiarch", channel="2.0", architectures=["arm64", "riscv64"])
SIMPLE_BASENAME = bases.BaseName("simple", "0.0")
ONE_ARCH_BASENAME = bases.BaseName("arch", "1.0")
MULTIARCH_BASENAME = bases.BaseName("multiarch", "2.0")
UBUNTU_JAMMY = Base(name="ubuntu", channel="22.04", architectures=["amd64"])
SIMPLE_BASES = (
    UBUNTU_JAMMY,
    Base(name="centos", channel="7", architectures=["amd64"]),
    Base(name="almalinux", channel="9", architectures=["amd64"]),
)
COMPLEX_BASES = (
    Base(name="ubuntu", channel="devel", architectures=["amd64", "arm64", "s390x", "riscv64"]),
    Base(name="almalinux", channel="9", architectures=["amd64", "arm64", "s390x", "ppc64el"]),
)
SIMPLE_BASE_CONFIG_DICT = {"name": "ubuntu", "channel": "22.04"}
FULL_BASE_CONFIG_DICT = {
    "build-on": [{"channel": "22.04", "name": "ubuntu"}],
    "run-on": [{"channel": "22.04", "name": "ubuntu"}],
}

MINIMAL_CHARMCRAFT_YAML = """\
type: charm
bases: [{name: ubuntu, channel: "22.04", architectures: [arm64]}]
"""
SIMPLE_METADATA_YAML = "{name: charmy-mccharmface, summary: Charmy!, description: Very charming!}"
SIMPLE_CHARMCRAFT_YAML = """\
type: charm
name: charmy-mccharmface
summary: Charmy!
description: Very charming!
bases: [{name: ubuntu, channel: "22.04", architectures: [arm64]}]
"""
SIMPLE_CONFIG_YAML = "options: {admin: {default: root, description: Admin user, type: string}}"
SIMPLE_CONFIG_DICT = {
    "options": {"admin": {"type": "string", "default": "root", "description": "Admin user"}}
}
SIMPLE_ACTIONS_YAML = "snooze: {description: Take a little nap.}"
SIMPLE_ACTIONS_DICT = {"snooze": {"description": "Take a little nap."}}


# region CharmPlatform tests
@pytest.mark.parametrize(
    ("bases", "expected"),
    [
        (
            [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
            "xname-xchannel-xarch1",
        ),
        (
            [
                Base(
                    name="xname",
                    channel="xchannel",
                    architectures=["xarch1", "xarch2", "xarch3"],
                )
            ],
            "xname-xchannel-xarch1-xarch2-xarch3",
        ),
        (
            [
                Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                Base(
                    name="x2name",
                    channel="x2channel",
                    architectures=["x2arch1", "x2arch2"],
                ),
            ],
            "x1name-x1channel-x1arch_x2name-x2channel-x2arch1-x2arch2",
        ),
    ],
)
def test_platform_from_bases_backwards_compatible(bases, expected):
    """Replicates the format_charm_file_name tests in test_package.py.

    This ensures that charm names remain consistent as we move to platforms.
    """
    assert project.CharmPlatform.from_bases(bases) == expected


@pytest.mark.parametrize("base", [*SIMPLE_BASES, *COMPLEX_BASES])
def test_platform_from_single_base(base):
    """Tests generating a platform name from a real (single) base."""
    expected_architectures = "-".join(base.architectures)
    expected = f"{base.name}-{base.channel}-{expected_architectures}"

    actual = project.CharmPlatform.from_bases([base])

    assert actual == expected


@pytest.mark.parametrize(
    ("bases", "expected"),
    [
        (SIMPLE_BASES, "ubuntu-22.04-amd64_centos-7-amd64_almalinux-9-amd64"),
        (
            COMPLEX_BASES,
            "ubuntu-devel-amd64-arm64-s390x-riscv64_almalinux-9-amd64-arm64-s390x-ppc64el",
        ),
    ],
)
def test_platform_from_multiple_bases(bases, expected):
    assert project.CharmPlatform.from_bases(bases) == expected


# endregion
# region Platform tests
VALID_PLATFORM_ARCHITECTURES = [
    *(
        list(x) for x in itertools.combinations(const.CharmArch, 1)
    ),  # A single architecture in a list
    *(list(x) for x in itertools.combinations(const.CharmArch, 2)),  # Two architectures in a list
]


@pytest.mark.parametrize("build_on", VALID_PLATFORM_ARCHITECTURES)
@pytest.mark.parametrize("build_for", [[arch] for arch in (*const.CharmArch, "all")])
def test_platform_validation_lists(build_on, build_for):
    platform = project.Platform.parse_obj({"build-on": build_on, "build-for": build_for})

    assert platform.build_for == build_for
    assert platform.build_on == build_on


@pytest.mark.parametrize("build_on", const.CharmArch)
@pytest.mark.parametrize("build_for", [*const.CharmArch, "all"])
def test_platform_validation_strings(build_on, build_for):
    platform = project.Platform.parse_obj({"build-on": build_on, "build-for": build_for})

    assert platform.build_for == [build_for]
    assert platform.build_on == [build_on]


# endregion
# region CharmBuildInfo tests
@pytest.mark.parametrize("build_on_base", [SIMPLE_BASE, BASE_WITH_ONE_ARCH, BASE_WITH_MULTIARCH])
@pytest.mark.parametrize("build_on_arch", ["amd64", "arm64", "riscv64", "s390x"])
@pytest.mark.parametrize("run_on", [SIMPLE_BASE, BASE_WITH_ONE_ARCH])
def test_build_info_from_build_on_run_on_basic(
    build_on_base: Base,
    build_on_arch: str,
    run_on: Base,
):
    info = project.CharmBuildInfo.from_build_on_run_on(
        build_on_base, build_on_arch, [run_on], bases_index=10, build_on_index=256
    )

    pytest_check.equal(info.build_on, build_on_arch)
    pytest_check.equal(info.build_for_bases, [run_on])
    pytest_check.equal(info.build_for, run_on.architectures[0])
    pytest_check.equal(info.base.name, build_on_base.name)
    pytest_check.equal(info.base.version, build_on_base.channel)


@pytest.mark.parametrize(
    ("run_on", "expected"),
    [
        pytest.param(
            [BASE_WITH_MULTIARCH],
            "arm64-riscv64",
            id="one-base",
        ),
        pytest.param(
            [
                BASE_WITH_ONE_ARCH,
                Base(name="ubuntu", channel="24.04", architectures=["riscv64"]),
            ],
            "amd64-riscv64",
            id="multiarch-across-bases",
        ),
    ],
)
def test_build_info_from_build_on_run_on_multi_arch(run_on, expected):
    info = project.CharmBuildInfo.from_build_on_run_on(
        SIMPLE_BASE, "amd64", run_on, bases_index=10, build_on_index=256
    )

    assert info.build_for == expected


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                BasesConfiguration(
                    **{"build-on": [BASE_WITH_ONE_ARCH], "run-on": [BASE_WITH_ONE_ARCH]}
                )
            ],
            [
                project.CharmBuildInfo(
                    platform="arch-1.0-amd64",  # mypy: ignore[assignment]
                    build_on="amd64",
                    build_for="amd64",
                    base=ONE_ARCH_BASENAME,
                    build_for_bases=[BASE_WITH_ONE_ARCH],
                    bases_index=0,
                    build_on_index=0,
                )
            ],
        ),
    ],
)
def test_build_info_generator(given, expected):
    assert list(project.CharmBuildInfo.gen_from_bases_configurations(*given)) == expected


# endregion
# region Build planners
@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            {"type": "bundle"},
            [
                project.models.BuildInfo(
                    platform=utils.get_host_architecture(),
                    build_on=utils.get_host_architecture(),
                    build_for=utils.get_host_architecture(),
                    base=bases.BaseName(
                        name=utils.get_os_platform().system,
                        version=utils.get_os_platform().release,
                    ),
                ),
            ],
            id="bundle",
        ),
        pytest.param(
            {"base": "ubuntu@22.04", "platforms": {"amd64": None}},
            [
                project.models.BuildInfo(
                    platform="amd64",
                    build_on="amd64",
                    build_for="amd64",
                    base=bases.BaseName("ubuntu", "22.04"),
                )
            ],
            id="simple-platforms",
        ),
        pytest.param(
            {
                "base": "ubuntu@22.04",
                "platforms": {
                    "fancy": {"build-on": ["amd64", "arm64", "riscv64"], "build-for": ["all"]},
                    "crossy": {"build-on": "s390x", "build-for": "ppc64el"},
                    "amd64": None,
                    "arm64": None,
                    "riscv64": None,
                },
            },
            [
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="amd64",
                    build_for="all",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="arm64",
                    build_for="all",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="riscv64",
                    build_for="all",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="crossy",
                    build_on="s390x",
                    build_for="ppc64el",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="amd64",
                    build_on="amd64",
                    build_for="amd64",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="arm64",
                    build_on="arm64",
                    build_for="arm64",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="riscv64",
                    build_on="riscv64",
                    build_for="riscv64",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
            ],
            id="complex-platforms",
        ),
        pytest.param(
            {
                "base": "ubuntu@24.04",
                "build-base": "ubuntu@devel",
                "platforms": {"amd64": None},
            },
            [
                project.models.BuildInfo(
                    platform="amd64",
                    build_on="amd64",
                    build_for="amd64",
                    base=bases.BaseName("ubuntu", "devel"),
                )
            ],
            id="platforms-with-build-base",
        ),
        pytest.param(
            {"bases": [{"name": "ubuntu", "channel": "22.04"}]},
            [
                project.CharmBuildInfo(
                    platform=f"ubuntu-22.04-{utils.get_host_architecture()}",
                    build_on=utils.get_host_architecture(),
                    build_for=utils.get_host_architecture(),
                    build_for_bases=[project.charmcraft.Base(name="ubuntu", channel="22.04")],
                    build_on_index=0,
                    base=bases.BaseName("ubuntu", "22.04"),
                    bases_index=0,
                ),
            ],
            id="basic-bases",
        ),
        pytest.param(
            {"bases": [{"build-on": [BASE_WITH_ONE_ARCH], "run-on": [BASE_WITH_ONE_ARCH]}]},
            [
                project.CharmBuildInfo(
                    platform="arch-1.0-amd64",
                    build_on="amd64",
                    build_for="amd64",
                    build_for_bases=[BASE_WITH_ONE_ARCH],
                    build_on_index=0,
                    base=bases.BaseName("arch", "1.0"),
                    bases_index=0,
                ),
            ],
            id="arch-base",
        ),
    ],
)
def test_build_planner_correct(data, expected):
    planner = project.CharmcraftBuildPlanner.parse_obj(data)

    assert planner.get_build_plan() == expected


@pytest.mark.parametrize("base", ["ubuntu@20.04", "ubuntu@22.04", "ubuntu@24.04"])
@pytest.mark.parametrize(
    ("build_base", "build_plan_basename"),
    [
        ("ubuntu@20.04", bases.BaseName("ubuntu", "20.04")),
        ("ubuntu@22.04", bases.BaseName("ubuntu", "22.04")),
        ("ubuntu@24.04", bases.BaseName("ubuntu", "24.04")),
        ("almalinux@9", bases.BaseName("almalinux", "9")),
    ],
)
@pytest.mark.parametrize(
    "platforms",
    [
        {"amd64": None},
        {"amd64": None, "fancy": {"build-on": ["amd64", "riscv64"], "build-for": ["all"]}},
    ],
)
def test_build_planner_platforms_combinations(base, build_base, build_plan_basename, platforms):
    """Test that we're able to create a valid platform for each of these combinations."""
    planner = project.CharmcraftBuildPlanner(
        base=base,
        build_base=build_base,
        platforms=platforms,
    )
    plan = planner.get_build_plan()

    for build_info in plan:
        pytest_check.equal(build_info.base, build_plan_basename)
        pytest_check.is_in(build_info.platform, platforms.keys())


@pytest.mark.parametrize("architecture", sorted(const.SUPPORTED_ARCHITECTURES))
@pytest.mark.parametrize("system", ["ubuntu", "linux", "macos", "windows", "plan9"])
@pytest.mark.parametrize("release", ["22.04", "2.6.32", "10.5", "vista", "from bell labs"])
def test_get_bundle_plan(mocker, architecture, release, system):
    mocker.patch("charmcraft.utils.get_host_architecture", return_value=architecture)
    mocker.patch(
        "charmcraft.utils.get_os_platform",
        return_value=utils.OSPlatform(machine=architecture, system=system, release=release),
    )
    planner = project.CharmcraftBuildPlanner(type="bundle")

    assert planner.get_build_plan() == [
        models.BuildInfo(
            platform=architecture,
            build_on=architecture,
            build_for=architecture,
            base=bases.BaseName(system, release),
        )
    ]


# endregion
# region CharmcraftProject tests
@pytest.mark.parametrize(
    ("data", "type_class"),
    [
        (
            {
                "type": "charm",
                "name": "basic",
                "summary": "A basic charm",
                "description": "A thing",
                "bases": [SIMPLE_BASE_CONFIG_DICT],
            },
            project.Charm,
        ),
        (
            {"type": "bundle"},
            project.Bundle,
        ),
    ],
)
def test_unmarshal_success(data, type_class):
    assert isinstance(project.CharmcraftProject.unmarshal(data), type_class)


@pytest.mark.parametrize("type_", [None, "", "invalid", "Dvorak"])
def test_unmarshal_invalid_type(type_):
    with pytest.raises(ValueError, match="^field type cannot be "):
        project.CharmcraftProject.unmarshal({"type": type_})


@pytest.mark.parametrize(("charmcraft_yaml", "expected_diff"), [(SIMPLE_CHARMCRAFT_YAML, {},),])
def test_from_yaml_file_success(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    simple_charm,
    charmcraft_yaml: str,
    expected_diff: dict[str, Any],
):
    expected_dict = simple_charm.marshal()
    expected_dict.update(expected_diff)
    expected = project.CharmcraftProject.unmarshal(expected_dict)

    fs.create_file("/charmcraft.yaml", contents=charmcraft_yaml)

    actual = project.CharmcraftProject.from_yaml_file(pathlib.Path("/charmcraft.yaml"))

    assert actual.marshal() == expected.marshal()


@pytest.mark.parametrize(
    (
        "charmcraft_yaml",
        "exc_class",
        "match",
        "details",
    ),
    [
        pytest.param(
            None,
            CraftError,
            r"^Could not find charmcraft\.yaml at '.charmcraft\.yaml'$",
            None,
            id="FileNotFound",
        ),
    ],
)
def test_from_yaml_file_exception(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    charmcraft_yaml: str | None,
    exc_class: type[CraftError],
    match: str,
    details: str,
):
    if charmcraft_yaml:
        fs.create_file("/charmcraft.yaml", contents=charmcraft_yaml)

    with pytest.raises(exc_class, match=match) as exc:
        project.CharmcraftProject.from_yaml_file(pathlib.Path("/charmcraft.yaml"))

    assert exc.value.details == details


# endregion
# region Charm tests
@pytest.mark.parametrize(
    ("values", "expected_changes"),
    [
        pytest.param(
            {"bases": [SIMPLE_BASE_CONFIG_DICT]},
            {"bases": [FULL_BASE_CONFIG_DICT]},
            id="simple-base",
        ),
    ],
)
def test_instantiate_bases_charm_success(values: dict[str, Any], expected_changes: dict[str, Any]):
    """Various successful instantiations of a charm project."""
    values.update(
        {
            "type": "charm",
            "name": "test-charm",
            "summary": "A test charm",
            "description": "A test charm model that can be successfully instantiated.",
        }
    )
    expected = values.copy()
    expected.update(expected_changes)

    actual = project.BasesCharm(**values)

    assert actual.marshal() == expected


@pytest.mark.parametrize(
    ("values", "error_cls", "error_match"),
    [
        pytest.param(
            {
                "type": "charm",
                "name": "test-charm",
                "summary": "A test charm",
                "description": "This charm has no bases and is thus invalid.",
            },
            pydantic.ValidationError,
            r"bases\s+field required",
            id="no-bases",
        ),
        pytest.param(
            {
                "type": "charm",
                "name": "test-charm",
                "summary": "A test charm",
                "description": "Empty bases, also invalid.",
                "bases": [],
            },
            pydantic.ValidationError,
            r"bases\s+ensure this value has at least 1 item",
            id="empty-bases",
        ),
    ],
)
def test_instantiate_bases_charm_error(
    values: dict[str, Any], error_cls: type[Exception], error_match: str
):
    with pytest.raises(error_cls, match=error_match):
        project.BasesCharm(**values)


@pytest.mark.parametrize("base", ["ubuntu@24.04"])
def test_devel_bases(monkeypatch, base):
    monkeypatch.setattr(const, "DEVEL_BASE_STRINGS", [base])

    with pytest.raises(
        pydantic.ValidationError,
        match=r"requires a build-base \(recommended: 'build-base: ubuntu@devel'\)",
    ):
        project.PlatformCharm(
            type="charm",
            name="test-charm",
            summary="",
            description="",
            base=base,
            platforms={"amd64": None},
            parts={"charm": {"plugin": "charm"}},
        )


@pytest.mark.parametrize(
    "filename", [f.name for f in (pathlib.Path(__file__).parent / "valid_charms_yaml").iterdir()]
)
def test_read_charm_from_yaml_file_self_contained_success(tmp_path, filename: str):
    file_path = pathlib.Path(__file__).parent / "valid_charms_yaml" / filename
    with file_path.open() as f:
        expected_dict = safe_yaml_load(f)

    charm = project.CharmcraftProject.from_yaml_file(file_path)

    # The JSON round-trip here is to get rid of any Pydantic constraint objects like AnyHttpUrl
    assert json.loads(json.dumps(charm.marshal())) == expected_dict


@pytest.mark.parametrize(
    ("filename", "errors"),
    [
        (
            "basic.yaml",
            dedent(
                """\
                Bad basic.yaml content:
                - field 'name' required in top-level configuration
                - field 'summary' required in top-level configuration
                - field 'description' required in top-level configuration
                - field 'bases' required in top-level configuration"""
            ),
        ),
        (
            "invalid-type.yaml",
            dedent(
                """\
                Bad invalid-type.yaml content:
                - field 'name' required in top-level configuration
                - field 'summary' required in top-level configuration
                - field 'description' required in top-level configuration
                - unexpected value; permitted: 'charm' (in field 'type')
                - field 'bases' required in top-level configuration"""
            ),
        ),
        (
            "invalid-base.yaml",
            dedent(
                """\
                Bad invalid-base.yaml content:
                - Base requires 'platforms' definition: {'name': 'ubuntu', 'channel': '24.04'} (in field 'bases[0]')
                - Base requires 'platforms' definition: {'name': 'ubuntu', 'channel': 'devel'} (in field 'bases[1]')"""
            ),
        ),
    ],
)
def test_read_charm_from_yaml_file_error(filename, errors):
    file_path = pathlib.Path(__file__).parent / "invalid_charms_yaml" / filename

    with pytest.raises(CraftValidationError) as exc:
        _ = project.BasesCharm.from_yaml_file(file_path)

    assert exc.value.args[0] == errors


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        ({"name": "ubuntu", "channel": "18.04"}, True),
        ({"name": "ubuntu", "channel": "20.04"}, True),
        ({"name": "ubuntu", "channel": "22.04"}, True),
        ({"name": "ubuntu", "channel": "23.04"}, True),
        ({"name": "ubuntu", "channel": "23.10"}, True),
        ({"name": "ubuntu", "channel": "24.04"}, False),
        ({"name": "ubuntu", "channel": "24.10"}, False),
        ({"name": "ubuntu", "channel": "25.04"}, False),
        ({"name": "centos", "channel": "7"}, True),
        ({"name": "almalinux", "channel": "9"}, True),
    ],
)
def test_check_legacy_bases(base, expected):
    assert project.BasesCharm._check_base_is_legacy(base) == expected


# endregion
