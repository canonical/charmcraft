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
import textwrap
from textwrap import dedent
from typing import Any

import hypothesis
import pydantic
import pyfakefs.fake_filesystem
import pytest
import pytest_check
from craft_application import models, util
from craft_application.errors import CraftValidationError
from craft_application.util import safe_yaml_load
from craft_cli import CraftError
from craft_providers import bases
from hypothesis import strategies

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
    Base(
        name="ubuntu",
        channel="devel",
        architectures=["amd64", "arm64", "s390x", "riscv64"],
    ),
    Base(
        name="almalinux",
        channel="9",
        architectures=["amd64", "arm64", "s390x", "ppc64el"],
    ),
)
SIMPLE_BASE_CONFIG_DICT = {"name": "ubuntu", "channel": "22.04"}
FULL_BASE_CONFIG_DICT = {
    "build-on": [{"channel": "22.04", "name": "ubuntu"}],
    "run-on": [{"channel": "22.04", "name": "ubuntu"}],
}
BASIC_CHARM_PARTS = {"charm": {"plugin": "charm", "source": "."}}
BASIC_CHARM_PARTS_EXPANDED = {
    "charm": {
        "plugin": "charm",
        "source": ".",
        "charm-binary-python-packages": [],
        "charm-entrypoint": "src/charm.py",
        "charm-python-packages": [],
        "charm-requirements": [],
        "charm-strict-dependencies": False,
    }
}

MINIMAL_CHARMCRAFT_YAML = f"""\
type: charm
bases:
  - build-on:
      - name: ubuntu
        channel: "22.04"
        architectures: [{util.get_host_architecture()}]
    run-on:
      - name: ubuntu
        channel: "22.04"
        architectures: [arm64]
"""
SIMPLE_METADATA_YAML = "{name: charmy-mccharmface, summary: Charmy!, description: Very charming!}"
SIMPLE_CHARMCRAFT_YAML = f"""\
type: charm
name: charmy-mccharmface
summary: Charmy!
description: Very charming!
bases:
  - build-on:
      - name: ubuntu
        channel: "22.04"
        architectures: [{util.get_host_architecture()}]
    run-on:
      - name: ubuntu
        channel: "22.04"
        architectures: [arm64]
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
def test_platform_from_bases_backwards_compatible(bases: list[Base], expected: str):
    """Replicates the format_charm_file_name tests in test_package.py.

    This ensures that charm names remain consistent as we move to platforms.
    """
    assert project.get_charm_file_platform_str(bases) == expected


@pytest.mark.parametrize("base", [*SIMPLE_BASES, *COMPLEX_BASES])
def test_platform_from_single_base(base):
    """Tests generating a platform name from a real (single) base."""
    expected_architectures = "-".join(base.architectures)
    expected = f"{base.name}-{base.channel}-{expected_architectures}"

    actual = project.get_charm_file_platform_str([base])

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
    assert project.get_charm_file_platform_str(bases) == expected


# endregion
# region Platform tests
VALID_PLATFORM_ARCHITECTURES = [
    *(
        list(x) for x in itertools.combinations(const.CharmArch, 1)
    ),  # A single architecture in a list
    *(list(x) for x in itertools.combinations(const.CharmArch, 2)),  # Two architectures in a list
]


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
    ("lib_name", "expected_lib_name"),
    [
        ("charm.lib", "charm.lib"),
        ("charm_with_underscores.lib", "charm-with-underscores.lib"),
        ("charm-with-hyphens.lib", "charm-with-hyphens.lib"),
        ("charm.lib_with_hyphens", "charm.lib_with_hyphens"),
        ("charm0.number_0_lib", "charm0.number_0_lib"),
    ],
)
@pytest.mark.parametrize("lib_version", ["0", "1", "2.0", "2.1", "3.14"])
def test_create_valid_charm_lib(lib_name: str, expected_lib_name: str, lib_version: str):
    lib = project.CharmLib.unmarshal({"lib": lib_name, "version": lib_version})
    assert lib.lib == expected_lib_name


@pytest.mark.parametrize(
    ("name", "error_match"),
    [
        (
            "boop",
            r"Library name invalid. Expected '\[charm_name\].\[lib_name\]', got 'boop'",
        ),
        (
            "Invalid charm name.valid_lib",
            "Invalid charm name for lib 'Invalid charm name.valid_lib'. Value 'Invalid charm name' is invalid",
        ),
        (
            "my_charm.invalid-library-name",
            "Library name 'invalid-library-name' is invalid. Library names must be valid Python module names.",
        ),
    ],
)
def test_invalid_charm_lib_name(name: str, error_match: str):
    with pytest.raises(pydantic.ValidationError, match=error_match):
        project.CharmLib.unmarshal({"lib": name, "version": "0"})


@hypothesis.given(
    strategies.one_of(
        strategies.floats(
            min_value=0.001,
            max_value=2**32,
            allow_nan=False,
            allow_infinity=False,
            allow_subnormal=False,
        ),
        strategies.integers(min_value=0, max_value=2**32),
    )
)
def test_valid_library_version(version: float):
    project.CharmLib.unmarshal({"lib": "charm_name.lib_name", "version": str(version)})


@pytest.mark.parametrize("version", [".1", "NaN", ""])
def test_invalid_api_version(version: str):
    with pytest.raises(
        pydantic.ValidationError,
        match="API version not valid. Expected an integer, got '",
    ):
        project.CharmLib(lib="charm_name.lib_name", version=version)


@pytest.mark.parametrize("version", ["1.", "1.number"])
def test_invalid_patch_version(version: str):
    with pytest.raises(
        pydantic.ValidationError,
        match="Patch version not valid. Expected an integer, got '",
    ):
        project.CharmLib(lib="charm_name.lib_name", version=version)


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
                    platform=util.get_host_architecture(),
                    build_on=util.get_host_architecture(),
                    build_for=util.get_host_architecture(),
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
                    "fancy": {
                        "build-on": ["amd64", "arm64", "riscv64"],
                        "build-for": ["s390x"],
                    },
                    "crossy": {"build-on": ["s390x"], "build-for": ["ppc64el"]},
                    "amd64": None,
                    "arm64": None,
                    "riscv64": None,
                },
            },
            [
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="amd64",
                    build_for="s390x",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="arm64",
                    build_for="s390x",
                    base=bases.BaseName("ubuntu", "22.04"),
                ),
                project.models.BuildInfo(
                    platform="fancy",
                    build_on="riscv64",
                    build_for="s390x",
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
                    platform=f"ubuntu-22.04-{util.get_host_architecture()}",
                    build_on=util.get_host_architecture(),
                    build_for=util.get_host_architecture(),
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
    planner = project.CharmcraftBuildPlanner.model_validate(data)

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
        {
            "amd64": None,
            "fancy": {"build-on": ["amd64", "riscv64"], "build-for": ["riscv64"]},
        },
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
    mocker.patch("craft_application.util.get_host_architecture", return_value=architecture)
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


@pytest.mark.parametrize(
    (
        "charmcraft_yaml",
        "metadata_yaml",
        "config_yaml",
        "actions_yaml",
        "expected_diff",
    ),
    [
        (
            SIMPLE_CHARMCRAFT_YAML,
            None,
            None,
            None,
            {"parts": BASIC_CHARM_PARTS},
        ),
        (
            MINIMAL_CHARMCRAFT_YAML,
            SIMPLE_METADATA_YAML,
            None,
            None,
            {"parts": BASIC_CHARM_PARTS},
        ),
        (
            SIMPLE_CHARMCRAFT_YAML,
            None,
            SIMPLE_CONFIG_YAML,
            None,
            {"config": SIMPLE_CONFIG_DICT, "parts": BASIC_CHARM_PARTS},
        ),
        (
            SIMPLE_CHARMCRAFT_YAML,
            None,
            None,
            SIMPLE_ACTIONS_YAML,
            {"actions": SIMPLE_ACTIONS_DICT, "parts": BASIC_CHARM_PARTS},
        ),
        (
            MINIMAL_CHARMCRAFT_YAML,
            SIMPLE_METADATA_YAML,
            SIMPLE_CONFIG_YAML,
            SIMPLE_ACTIONS_YAML,
            {
                "actions": SIMPLE_ACTIONS_DICT,
                "config": SIMPLE_CONFIG_DICT,
                "parts": BASIC_CHARM_PARTS,
            },
        ),
        pytest.param(
            SIMPLE_CHARMCRAFT_YAML
            + textwrap.dedent(
                """\
                parts:
                  charm: {}
                  reactive: {}
                  bundle: {}
                """
            ),
            None,
            None,
            None,
            {
                "parts": {
                    "charm": {
                        "plugin": "charm",
                        "source": ".",
                    },
                    "reactive": {
                        "plugin": "reactive",
                    },
                    "bundle": {
                        "plugin": "bundle",
                        "source": ".",
                    },
                }
            },
            id="implicit-parts-plugins",
        ),
    ],
)
def test_from_yaml_file_success(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    simple_charm,
    charmcraft_yaml: str,
    metadata_yaml: str | None,
    config_yaml: str | None,
    actions_yaml: str | None,
    expected_diff: dict[str, Any],
):
    expected_dict = simple_charm.marshal().copy()
    expected_dict.update(expected_diff)

    fs.create_file("/charmcraft.yaml", contents=charmcraft_yaml)
    if metadata_yaml:
        fs.create_file("/metadata.yaml", contents=metadata_yaml)
    if config_yaml:
        fs.create_file("/config.yaml", contents=config_yaml)
    if actions_yaml:
        fs.create_file("/actions.yaml", contents=actions_yaml)

    actual = project.CharmcraftProject.from_yaml_file(pathlib.Path("/charmcraft.yaml"))

    assert actual.marshal() == expected_dict


@pytest.mark.parametrize(
    (
        "charmcraft_yaml",
        "metadata_yaml",
        "config_yaml",
        "actions_yaml",
        "exc_class",
        "match",
        "details",
    ),
    [
        pytest.param(
            None,
            None,
            None,
            None,
            CraftError,
            r"^Could not find charmcraft\.yaml at '.charmcraft\.yaml'$",
            None,
            id="FileNotFound",
        ),
        pytest.param(
            f"{SIMPLE_CHARMCRAFT_YAML}\nconfig: ",
            None,
            SIMPLE_CONFIG_YAML,
            None,
            CraftValidationError,
            r"^Cannot specify 'config' section",
            None,
            id="duplicate-config",
        ),
        pytest.param(
            f"{SIMPLE_CHARMCRAFT_YAML}\nactions:",
            None,
            None,
            SIMPLE_ACTIONS_YAML,
            CraftValidationError,
            r"^Cannot specify 'actions' section",
            None,
            id="duplcate-actions",
        ),
    ],
)
def test_from_yaml_file_exception(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    charmcraft_yaml: str | None,
    metadata_yaml: str | None,
    config_yaml: str | None,
    actions_yaml: str | None,
    exc_class: type[CraftError],
    match: str,
    details: str,
):
    if charmcraft_yaml:
        fs.create_file("/charmcraft.yaml", contents=charmcraft_yaml)
    if metadata_yaml:
        fs.create_file("/metadata.yaml", contents=metadata_yaml)
    if config_yaml:
        fs.create_file("/config.yaml", contents=config_yaml)
    if actions_yaml:
        fs.create_file("/actions.yaml", contents=actions_yaml)

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
            r"bases\s+Field required",
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
            r"bases\s+List should have at least 1 item",
            id="empty-bases",
        ),
    ],
)
def test_instantiate_bases_charm_error(
    values: dict[str, Any], error_cls: type[Exception], error_match: str
):
    with pytest.raises(error_cls, match=error_match):
        project.BasesCharm(**values)


@pytest.mark.parametrize("base", ["ubuntu@18.04", "ubuntu@22.04"])
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
    "filename",
    [f.name for f in (pathlib.Path(__file__).parent / "valid_charms_yaml").iterdir()],
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
                - input should be 'charm' (in field 'type')
                - field 'bases' required in top-level configuration"""
            ),
        ),
        (
            "invalid-base.yaml",
            dedent(
                """\
                Bad invalid-base.yaml content:
                - base requires 'platforms' definition: {'name': 'ubuntu', 'channel': '24.04'} (in field 'bases[0]')
                - base requires 'platforms' definition: {'name': 'ubuntu', 'channel': 'devel'} (in field 'bases[1]')"""
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
    assert project._check_base_is_legacy(base) == expected


# endregion
