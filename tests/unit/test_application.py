# Copyright 2020-2023 Canonical Ltd.
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
"""Unit tests for application class."""
import textwrap
from unittest import mock

import craft_application
import craft_cli.pytest_plugin
import pyfakefs.fake_filesystem
import pytest
from craft_application import util

from charmcraft import application, errors, services
from charmcraft.application.main import PRIME_BEHAVIOUR_CHANGE_MESSAGE


@pytest.mark.parametrize(
    ("charmcraft_dict", "metadata_yaml"),
    [
        (
            {},
            textwrap.dedent(
                """\
                name: test-charm
                summary: A test charm
                description: A charm for testing!"""
            ),
        ),
        (
            {"name": "test-charm"},
            textwrap.dedent(
                """\
                summary: A test charm
                description: A charm for testing!"""
            ),
        ),
        (
            {"name": "test-charm", "summary": "A test charm"},
            textwrap.dedent(
                """\
                description: A charm for testing!"""
            ),
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
            },
            textwrap.dedent(
                """\
                something-else: yes
                """
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    "expected",
    [{"name": "test-charm", "summary": "A test charm", "description": "A charm for testing!"}],
)
def test_extra_yaml_transform_success(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    service_factory,
    charmcraft_dict,
    metadata_yaml,
    expected,
):
    """Test that _extra_yaml_transform correctly transforms the data."""
    fs.create_file("metadata.yaml", contents=metadata_yaml)
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    actual = app._extra_yaml_transform(charmcraft_dict, build_on="amd64", build_for=None)

    assert actual == expected


@pytest.mark.parametrize(
    ("charmcraft_dict", "metadata_yaml", "message"),
    [
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
            },
            "",
            "Invalid file: 'metadata.yaml'",
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
            },
            textwrap.dedent(
                """\
                name: test-charm
                summary: A test charm
                description: A charm for testing!"""
            ),
            "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
        ),
    ],
)
def test_extra_yaml_transform_failure(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
    service_factory,
    charmcraft_dict,
    metadata_yaml,
    message,
):
    fs.create_file("metadata.yaml", contents=metadata_yaml)
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    with pytest.raises(errors.CraftError) as exc_info:
        app._extra_yaml_transform(charmcraft_dict, build_for=None, build_on="amd64")

    assert exc_info.value.args[0] == message


@pytest.mark.parametrize(
    ("charmcraft_dict"),
    [
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"charm": {"prime": ["something"]}},
            }
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"bundle": {"prime": ["something"]}},
            }
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"reactive": {"prime": ["something"]}},
            }
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"other_name": {"plugin": "charm", "prime": ["something"]}},
            }
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"other_name": {"plugin": "bundle", "prime": ["something"]}},
            }
        ),
        (
            {
                "name": "test-charm",
                "summary": "A test charm",
                "description": "A charm for testing!",
                "parts": {"other_name": {"plugin": "reactive", "prime": ["something"]}},
            }
        ),
    ],
)
def test_deprecated_prime_warning(
    emitter,
    service_factory,
    charmcraft_dict,
):
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app._extra_yaml_transform(charmcraft_dict, build_for=None, build_on="amd64")

    emitter.assert_progress(PRIME_BEHAVIOUR_CHANGE_MESSAGE, permanent=True)


@pytest.mark.parametrize(
    "base_charm",
    [
        {
            "name": "test-charm",
            "summary": "A test charm",
            "description": "A charm for testing!",
        },
    ],
)
@pytest.mark.parametrize(
    ("parts"),
    [
        pytest.param({}, id="no-parts"),
        pytest.param(
            {
                "parts": {"charm": {}},
            },
            id="named-charm",
        ),
        pytest.param({"parts": {"my-part": {"plugin": "charm"}}}, id="charm-plugin"),
        pytest.param(
            {
                "parts": {"reactive": {}},
            },
            id="named-reactive",
        ),
        pytest.param({"parts": {"my-part": {"plugin": "reactive"}}}, id="reactive-plugin"),
        pytest.param(
            {
                "parts": {"bundle": {}},
            },
            id="named-bundle",
        ),
        pytest.param({"parts": {"my-part": {"plugin": "bundle"}}}, id="bundle-plugin"),
    ],
)
def test_deprecated_prime_warning_not_raised(
    emitter,
    service_factory: services.CharmcraftServiceFactory,
    base_charm: dict[str, str],
    parts: dict[str, dict[str, str]],
):
    charmcraft_dict = base_charm | parts
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app._extra_yaml_transform(charmcraft_dict, build_for=None, build_on="amd64")

    with pytest.raises(AssertionError, match="^Expected call"):
        emitter.assert_progress(PRIME_BEHAVIOUR_CHANGE_MESSAGE, permanent=True)


@pytest.mark.parametrize(
    "charm_yaml",
    [
        {
            "name": "test-charm",
            "summary": "A test charm",
            "description": "A charm for testing!",
            "parts": {"charm": {"prime": ["something"]}},
        },
    ],
)
def test_deprecated_prime_warning_not_raised_in_managed_mode(
    monkeypatch, emitter, service_factory: services.CharmcraftServiceFactory, charm_yaml
):
    monkeypatch.setenv("CRAFT_MANAGED_MODE", "1")

    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app._extra_yaml_transform(charm_yaml, build_for=None, build_on="riscv64")


@pytest.mark.parametrize(
    "build_for",
    [
        "amd64-arm64",
        "s390x-ppc64el-riscv64",
    ],
)
def test_expand_environment_multi_arch(
    monkeypatch: pytest.MonkeyPatch,
    emitter: craft_cli.pytest_plugin.RecordingEmitter,
    service_factory: services.CharmcraftServiceFactory,
    build_for,
) -> None:
    mock_parent_expand_environment = mock.Mock()
    monkeypatch.setattr(
        craft_application.Application, "_expand_environment", mock_parent_expand_environment
    )
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app._expand_environment({}, build_for)

    emitter.assert_debug(
        "Expanding environment variables with the host architecture "
        f"{util.get_host_architecture()!r} as the build-for architecture "
        "because multiple run-on architectures were specified."
    )
