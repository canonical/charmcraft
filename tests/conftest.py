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
import os
import pathlib
import tempfile
import types
from collections.abc import Iterator
from unittest import mock

import craft_parts
import pytest
import responses as responses_module
import yaml
from craft_application import models, util
from craft_parts import callbacks, plugins
from craft_providers import bases

import charmcraft.parts
from charmcraft import const, env, instrum, parts, services, store
from charmcraft.application.main import APP_METADATA
from charmcraft.models import project


@pytest.fixture
def simple_charm():
    return project.BasesCharm(
        type="charm",
        name="charmy-mccharmface",
        summary="Charmy!",
        description="Very charming!",
        bases=[
            {
                "build-on": [
                    {
                        "name": "ubuntu",
                        "channel": "22.04",
                        "architectures": [util.get_host_architecture()],
                    }
                ],
                "run-on": [{"name": "ubuntu", "channel": "22.04", "architectures": ["arm64"]}],
            }
        ],
    )


@pytest.fixture
def mock_store_client():
    client = mock.Mock(spec_set=store.Client)

    client.whoami.return_value = {
        "account": {"username": "test-user"},
    }

    return client


@pytest.fixture
def mock_store_anonymous_client() -> mock.Mock:
    return mock.Mock(spec_set=store.AnonymousClient)


@pytest.fixture
def service_factory(
    fs,
    fake_project_dir,
    fake_prime_dir,
    simple_charm,
    mock_store_client,
    mock_store_anonymous_client,
    default_build_plan,
) -> services.CharmcraftServiceFactory:
    factory = services.CharmcraftServiceFactory(app=APP_METADATA)

    factory.set_kwargs(
        "package",
        project_dir=fake_project_dir,
        build_plan=default_build_plan,
    )
    factory.set_kwargs(
        "lifecycle",
        work_dir=pathlib.Path("/project"),
        cache_dir=pathlib.Path("/cache"),
        build_plan=default_build_plan,
    )

    factory.project = simple_charm

    factory.store.client = mock_store_client
    factory.store.anonymous_client = mock_store_anonymous_client

    return factory


@pytest.fixture
def default_build_plan():
    arch = util.get_host_architecture()
    return [
        models.BuildInfo(
            base=bases.BaseName("ubuntu", "22.04"),
            build_on=arch,
            build_for="arm64",
            platform="distro-1-test64",
        )
    ]


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
def global_debug():
    os.environ["CRAFT_DEBUG"] = "1"


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
def responses():
    """Simple helper to use responses module as a fixture, for easier integration in tests."""
    with responses_module.RequestsMock() as rsps:
        yield rsps


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
def prepare_actions_yaml(tmp_path: pathlib.Path):
    """Helper to create a actions.yaml file in disk.

    If content is not given, remove actions.yaml if exists.
    """
    return prepare_file(tmp_path, const.JUJU_ACTIONS_FILENAME)


@pytest.fixture
def prepare_config_yaml(tmp_path: pathlib.Path):
    """Helper to create a config.yaml file in disk.

    If content is not given, remove config.yaml if exists.
    """
    return prepare_file(tmp_path, const.JUJU_CONFIG_FILENAME)


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
                pytest.fail(f"Line {match_line!r} not found in the output found:\n{printed_repr}")

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
    from charmcraft.extensions import registry

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
    plugin_properties = parts.CharmPluginProperties.unmarshal(spec)
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

    return plugins.get_plugin(part=part, part_info=part_info, properties=plugin_properties)


@pytest.fixture
def bundle_plugin(tmp_path):
    project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
    spec = {
        "plugin": "bundle",
        "source": str(tmp_path),
    }
    plugin_properties = charmcraft.parts.bundle.BundlePluginProperties.unmarshal(spec)
    part_spec = plugins.extract_part_properties(spec, plugin_name="bundle")
    part = craft_parts.Part(
        "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
    )
    project_info = craft_parts.ProjectInfo(
        application_name="test",
        project_dirs=project_dirs,
        cache_dir=tmp_path,
    )
    part_info = craft_parts.PartInfo(project_info=project_info, part=part)

    return plugins.get_plugin(part=part, part_info=part_info, properties=plugin_properties)
