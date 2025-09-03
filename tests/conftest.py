# Copyright 2020-2024 Canonical Ltd.
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

import contextlib
import importlib
import json
import pathlib
import platform
import tempfile
import types
from collections.abc import Iterator
from typing import Any, cast
from unittest import mock

import craft_application
import craft_parts
import craft_platforms
import craft_store
import distro
import pytest
import yaml
from craft_application import util
from craft_parts import callbacks, plugins

import charmcraft.parts
from charmcraft import const, env, instrum, parts, services, store
from charmcraft.application.main import APP_METADATA
from charmcraft.extensions import registry
from charmcraft.models import project
from charmcraft.services.store import StoreService

FAKE_BASES_CHARM_TEMPLATE = """\
name: example-charm
summary: An example charm with bases
description: |
  A description for an example charm with bases.
type: charm
bases:
  - name: ubuntu
    channel: "{series}"

parts:
  charm:
    plugin: charm

"""

FAKE_PLATFORMS_CHARM_TEMPLATE = """\
name: example-charm
summary: An example charm with platforms
description: |
  A description for an example charm with platforms.
type: charm
base: {base}
build-base: {build_base}
platforms:
  amd64:
  arm64:
  riscv64:
  s390x:

parts:
  charm:
    plugin: charm
"""


@pytest.fixture
def basic_charm_dict() -> dict[str, Any]:
    return {
        "type": "charm",
        "name": "charmy-mccharmface",
        "summary": "Charmy!",
        "description": "Very charming!",
    }


@pytest.fixture
def simple_charm(basic_charm_dict: dict[str, Any]):
    return project.BasesCharm.unmarshal(
        basic_charm_dict
        | {
            "bases": [
                {
                    "build-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": [util.get_host_architecture()],
                        }
                    ],
                    "run-on": [
                        {
                            "name": "ubuntu",
                            "channel": "22.04",
                            "architectures": ["arm64"],
                        }
                    ],
                }
            ],
        }
    )


@pytest.fixture
def mock_store_client():
    client = mock.Mock(spec_set=store.Client)

    client.whoami.return_value = {
        "account": {"username": "test-user"},
    }

    return client


@pytest.fixture(scope="session", params=["bases", "platforms"])
def fake_project_yaml(request: pytest.FixtureRequest) -> Iterator[str]:
    current_base = craft_platforms.DistroBase.from_linux_distribution(
        distro.LinuxDistribution(
            include_lsb=True, include_uname=False, include_oslevel=False
        )
    )
    if platform.system() != "Linux":
        base_str = "ubuntu@24.04"
        series = "24.04"
    else:
        base_str = str(current_base)
        series = current_base.series

    if request.param == "bases":
        with pytest.MonkeyPatch.context() as monkeypatch:
            # Add the current system to legacy bases so we can test legacy bases.
            monkeypatch.setattr(const, "LEGACY_BASES", (*const.LEGACY_BASES, base_str))
            yield FAKE_BASES_CHARM_TEMPLATE.format(series=series)
        return
    yield FAKE_PLATFORMS_CHARM_TEMPLATE.format(
        base=base_str,
        build_base="ubuntu@devel",
    )


@pytest.fixture
def fake_project_file(project_path, fake_project_yaml):
    project_file = project_path / "charmcraft.yaml"
    project_file.write_text(fake_project_yaml)

    return project_file


@pytest.fixture
def mock_store_anonymous_client() -> mock.Mock:
    return mock.Mock(spec_set=store.AnonymousClient)


@pytest.fixture
def mock_publisher_gateway() -> mock.Mock:
    return mock.Mock(spec_set=craft_store.PublisherGateway)


@pytest.fixture
def service_factory(
    fake_project_yaml,  # Needs the real filesystem.
    fs,
    fake_project_file,
    fake_prime_dir,
    simple_charm,
    mock_store_client,
    mock_store_anonymous_client,
    mock_publisher_gateway,
    project_path,
) -> craft_application.ServiceFactory:
    services.register_services()
    factory = craft_application.ServiceFactory(app=APP_METADATA)

    factory.update_kwargs(
        "project",
        project_dir=project_path,
    )
    factory.update_kwargs(
        "lifecycle",
        work_dir=project_path,
        cache_dir=pathlib.Path("/cache"),
    )
    factory.update_kwargs(
        "charm_libs",
        project_dir=project_path,
    )

    factory.get("project").configure(
        platform=None,
        build_for=None,
    )
    factory.get("state").set(
        "charmcraft", "started_at", value="2020-03-14T00:00:00+00:00"
    )

    store_svc = cast(StoreService, factory.get("store"))
    store_svc.client = mock_store_client
    store_svc.anonymous_client = mock_store_anonymous_client
    store_svc._publisher = mock_publisher_gateway

    return factory


@pytest.fixture
def default_build_info() -> craft_platforms.BuildInfo:
    arch = util.get_host_architecture()
    return craft_platforms.BuildInfo(
        build_base=craft_platforms.DistroBase("ubuntu", "22.04"),
        build_on=arch,
        build_for="arm64",
        platform="distro-1-test64",
    )


@pytest.fixture
def fake_project_dir(fs) -> pathlib.Path:
    project_dir = pathlib.Path("/root/project")
    fs.create_dir(project_dir)
    return project_dir


@pytest.fixture
def fake_prime_dir(fs) -> pathlib.Path:
    prime_dir = pathlib.Path("/root/prime")
    fs.create_dir(prime_dir)
    return prime_dir


@pytest.fixture
def fake_path(fs) -> Iterator[pathlib.Path]:
    """Like tmp_path, but with a fake filesystem."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield pathlib.Path(tmp_dir)


@pytest.fixture
def new_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True, scope="session")
def tmpdir_under_tmpdir(tmpdir_factory):
    tempfile.tempdir = str(tmpdir_factory.getbasetemp())


@pytest.fixture(autouse=True, scope="session")
def setup_parts():
    parts.setup_parts()


@pytest.fixture
def charmhub_config() -> env.CharmhubConfig:
    """Provide a charmhub config for use in tests"""
    return env.CharmhubConfig(
        api_url="https://api.staging.charmhub.io",
        storage_url="https://storage.staging.snapcraftcontent.com",
        registry_url="https://registry.staging.jujucharms.com",
    )


@pytest.fixture(autouse=True)
def intertests_cleanups():
    """Run some cleanups between tests.

    Before each test:

    - reload the instrumentator module to start clean.

    After each test:

    - clear the already-notified structure for each test (this is needed as that
      structure is a module-level one (by design), so otherwise it will be dirty
      between tests).

    - unregister all Craft Parts plugins callbacks
    """
    importlib.reload(instrum)
    yield
    callbacks.unregister_all()


@pytest.fixture
def prepare_charmcraft_yaml(tmp_path: pathlib.Path):
    """Helper to create a charmcraft.yaml file in disk.

    If content is not given, remove charmcraft.yaml if exists.
    """

    charmcraft_yaml_path = tmp_path / const.CHARMCRAFT_FILENAME

    def prepare_charmcraft_yaml(content: str | None = None):
        if content is None:
            with contextlib.suppress(OSError):
                charmcraft_yaml_path.unlink(missing_ok=True)
        else:
            charmcraft_yaml_path.write_text(content)

        return tmp_path

    return prepare_charmcraft_yaml


def prepare_file(tmp_path: pathlib.Path, filename: str):
    """Helper to create a file under a temporary path."""

    path = tmp_path / filename

    def prepare(content: str | None = None):
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(content)

        return tmp_path

    return prepare


@pytest.fixture
def prepare_metadata_yaml(tmp_path: pathlib.Path):
    """Helper to create a metadata.yaml file in disk.

    If content is not given, remove metadata.yaml if exists.
    """
    return prepare_file(tmp_path, const.METADATA_FILENAME)


@pytest.fixture
def emitter(emitter):
    """Monkeypatch craft-cli's emitter fixture to easily test the JSON encoded output."""

    def assert_json_output(self, expected_content):
        """Get last output, which should be a message, and validate its content."""
        last_output = self.interactions[-1]
        output_type, raw_output = last_output.args
        assert output_type == "message", "Last command output is not 'message'"
        try:
            output_content = json.loads(raw_output)
        except json.decoder.JSONDecodeError:
            pytest.fail("Last command output is not valid JSON.")
        assert output_content == expected_content

    emitter.assert_json_output = types.MethodType(assert_json_output, emitter)
    return emitter


@pytest.fixture
def assert_output(capsys):
    """Assert that a given string was sent to stdout.

    This is a helper to simplify tests for charm_builder.py and its modules that print
    directly to stdout.

    Note that every call to this helper will clear the previous captured output.
    """

    def helper(*match_lines):
        captured = capsys.readouterr()
        printed_lines = captured.out.splitlines()
        for match_line in match_lines:
            if match_line not in printed_lines:
                printed_repr = "\n".join(map(repr, printed_lines))
                pytest.fail(
                    f"Line {match_line!r} not found in the output found:\n{printed_repr}"
                )

    return helper


@pytest.fixture
def build_charm_directory():
    def helper(tmp_path, fake_charms, file_type="charm"):
        expected = {}
        charmcraft_yaml = {"type": file_type}
        for name, path in fake_charms.items():
            full_path = tmp_path / path
            expected[name] = full_path
            full_path.mkdir(parents=True)
            metadata_yaml = {"name": name}
            with (full_path / const.CHARMCRAFT_FILENAME).open("w") as yaml_file:
                yaml.safe_dump(charmcraft_yaml, yaml_file)
            with (full_path / const.METADATA_FILENAME).open("w") as yaml_file:
                yaml.safe_dump(metadata_yaml, yaml_file)
        return expected

    return helper


@pytest.fixture
def stub_extensions(monkeypatch):
    extensions_dict = {}
    monkeypatch.setattr(registry, "_EXTENSIONS", extensions_dict)

    return extensions_dict


@pytest.fixture
def charm_plugin(tmp_path):
    requirement_files = ["reqs1.txt", "reqs2.txt"]
    for req in requirement_files:
        (tmp_path / req).write_text("somedep")
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {
        "plugin": "charm",
        "source": str(tmp_path),
        "charm-entrypoint": "entrypoint",
        "charm-binary-python-packages": ["pkg1", "pkg2"],
        "charm-python-packages": ["pkg3", "pkg4"],
        "charm-requirements": requirement_files,
    }
    plugin_properties = charmcraft.parts.plugins.CharmPluginProperties.unmarshal(spec)
    part_spec = plugins.extract_part_properties(spec, plugin_name="charm")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)

    return plugins.get_plugin(
        part=part, part_info=part_info, properties=plugin_properties
    )


@pytest.fixture
def poetry_plugin(tmp_path: pathlib.Path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {
        "plugin": "poetry",
        "source": str(tmp_path),
    }
    plugin_properties = parts.plugins.PoetryPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="poetry")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)

    return craft_parts.plugins.get_plugin(
        part=part, part_info=part_info, properties=plugin_properties
    )


@pytest.fixture
def python_plugin(tmp_path: pathlib.Path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {
        "plugin": "python",
        "source": str(tmp_path),
    }
    plugin_properties = parts.plugins.PythonPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="python")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)

    return craft_parts.plugins.get_plugin(
        part=part, part_info=part_info, properties=plugin_properties
    )


@pytest.fixture
def uv_plugin(tmp_path: pathlib.Path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {"plugin": "uv", "source": str(tmp_path)}
    plugin_properties = parts.plugins.UvPluginProperties.unmarshal(spec)
    part_spec = craft_parts.plugins.extract_part_properties(spec, plugin_name="uv")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info, part=part)

    return craft_parts.plugins.get_plugin(
        part=part, part_info=part_info, properties=plugin_properties
    )
