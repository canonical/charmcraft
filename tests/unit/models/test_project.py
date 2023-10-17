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
"""Tests for Charmcraft project-related models."""
import pathlib
from textwrap import dedent
from typing import Any, Dict, Type

import pydantic
import pytest
import pytest_check
from craft_application.errors import CraftValidationError
from craft_application.util import safe_yaml_load
from craft_providers import bases

from charmcraft.models import charmcraft, project

SIMPLE_BASE = charmcraft.Base(name="simple", channel="0.0")
BASE_WITH_ONE_ARCH = charmcraft.Base(name="arch", channel="1.0", architectures=["amd64"])
BASE_WITH_MULTIARCH = charmcraft.Base(
    name="multiarch", channel="2.0", architectures=["arm64", "riscv64"]
)
SIMPLE_BASENAME = bases.BaseName("simple", "0.0")
ONE_ARCH_BASENAME = bases.BaseName("arch", "1.0")
MULTIARCH_BASENAME = bases.BaseName("multiarch", "2.0")

SIMPLE_BASE_CONFIG_DICT = {"name": "ubuntu", "channel": "22.04"}
FULL_BASE_CONFIG_DICT = {
    "build-on": [{"channel": "22.04", "name": "ubuntu"}],
    "run-on": [{"channel": "22.04", "name": "ubuntu"}],
}


# region CharmBuildInfo tests
@pytest.mark.parametrize("build_on_base", [SIMPLE_BASE, BASE_WITH_ONE_ARCH, BASE_WITH_MULTIARCH])
@pytest.mark.parametrize("build_on_arch", ["amd64", "arm64", "riscv64", "s390x"])
@pytest.mark.parametrize("run_on", [SIMPLE_BASE, BASE_WITH_ONE_ARCH])
def test_build_info_from_build_on_run_on_basic(
    build_on_base: charmcraft.Base,
    build_on_arch: str,
    run_on: charmcraft.Base,
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
    "run_on",
    [
        pytest.param([], id="no-run-on-bases"),
        pytest.param(
            [BASE_WITH_MULTIARCH],
            id="one-base",
        ),
        pytest.param(
            [
                BASE_WITH_ONE_ARCH,
                charmcraft.Base(name="ubuntu", channel="24.04", architectures=["riscv64"]),
            ],
            id="multiarch-across-bases",
        ),
    ],
)
def test_build_info_from_build_on_run_on_multi_arch(run_on):
    info = project.CharmBuildInfo.from_build_on_run_on(
        SIMPLE_BASE, "amd64", run_on, bases_index=10, build_on_index=256
    )

    assert info.build_for == "multi"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                charmcraft.BasesConfiguration(
                    **{"build-on": [BASE_WITH_ONE_ARCH], "run-on": [BASE_WITH_ONE_ARCH]}
                )
            ],
            [
                project.CharmBuildInfo(
                    platform="arch-1.0-amd64",
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
# region CharmcraftProject tests
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
def test_instantiate_charm_success(values: Dict[str, Any], expected_changes: Dict[str, Any]):
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

    actual = project.Charm(**values)

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
def test_instantiate_charm_error(
    values: Dict[str, Any], error_cls: Type[Exception], error_match: str
):
    with pytest.raises(error_cls, match=error_match):
        project.Charm(**values)


@pytest.mark.parametrize(
    "filename", [f.name for f in (pathlib.Path(__file__).parent / "valid_charms_yaml").iterdir()]
)
def test_read_charm_from_yaml_file_self_contained_success(tmp_path, filename: str):
    file_path = pathlib.Path(__file__).parent / "valid_charms_yaml" / filename
    with file_path.open() as f:
        expected_dict = safe_yaml_load(f)

    charm = project.Charm.from_yaml_file(file_path)

    assert charm.marshal() == expected_dict


@pytest.mark.parametrize(
    ("filename", "errors"),
    [
        (
            "basic.yaml",
            dedent(
                """\
                Bad basic.yaml content:
                - field name required in top-level configuration
                - field summary required in top-level configuration
                - field description required in top-level configuration
                - field bases required in top-level configuration"""
            ),
        ),
        (
            "invalid-type.yaml",
            "Bad charmcraft.yaml content:\n- field type cannot be 'invalid'",
        ),
    ],
)
def test_read_charm_from_yaml_file_error(filename, errors):
    file_path = pathlib.Path(__file__).parent / "invalid_charms_yaml" / filename

    with pytest.raises(CraftValidationError) as exc:
        _ = project.Charm.from_yaml_file(file_path)

    assert exc.value.args[0] == errors


# endregion
