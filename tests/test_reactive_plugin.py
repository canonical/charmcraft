# Copyright 2021 Canonical Ltd.
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

import pathlib
import sys
from subprocess import CalledProcessError
from unittest.mock import call, patch

import craft_parts
import pydantic
import pytest
from craft_parts import plugins
from craft_parts.errors import PluginEnvironmentValidationError

from charmcraft import reactive_plugin

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")


@pytest.fixture
def charm_exe(tmp_path):
    """Provide a fake charm executable."""
    charm_bin = pathlib.Path(tmp_path, "mock_bin", "charm")
    charm_bin.parent.mkdir(exist_ok=True)
    charm_bin.write_text(
        '#!/bin/sh\necho "charmstore-client 2.5.1"\necho "charm-tools version 2.8.2"'
    )
    charm_bin.chmod(0o755)
    yield charm_bin


@pytest.fixture
def broken_charm_exe(tmp_path):
    """Provide a fake charm executable that fails to run."""
    charm_bin = pathlib.Path(tmp_path, "mock_bin", "charm")
    charm_bin.parent.mkdir(exist_ok=True)
    charm_bin.write_text('#!/bin/sh\nexit 1"')
    charm_bin.chmod(0o755)
    yield charm_bin


class TestReactivePlugin:
    """Ensure plugin methods return expected data."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, tmp_path):
        project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
        spec = {
            "plugin": "reactive",
            "source": str(tmp_path),
        }
        plugin_properties = reactive_plugin.ReactivePluginProperties.unmarshal(spec)
        part_spec = plugins.extract_part_properties(spec, plugin_name="reactive")
        part = craft_parts.Part(
            "foo", part_spec, project_dirs=project_dirs, plugin_properties=plugin_properties
        )
        project_info = craft_parts.ProjectInfo(
            application_name="test",
            project_dirs=project_dirs,
            cache_dir=tmp_path,
            project_name="fake-project",
        )
        part_info = craft_parts.PartInfo(project_info=project_info, part=part)

        self._plugin = plugins.get_plugin(
            part=part,
            part_info=part_info,
            properties=plugin_properties,
        )

    def test_get_build_package(self):
        assert self._plugin.get_build_packages() == set()

    def test_get_build_snaps(self):
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == {}

    def test_get_build_commands(self, tmp_path):
        assert self._plugin.get_build_commands() == [
            f"{sys.executable} -I {reactive_plugin.__file__} fake-project "
            f"{tmp_path}/parts/foo/build {tmp_path}/parts/foo/install",
        ]

    def test_invalid_properties(self):
        with pytest.raises(pydantic.ValidationError) as raised:
            reactive_plugin.ReactivePlugin.properties_class.unmarshal(
                {"source": ".", "reactive-invalid": True}
            )
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("reactive-invalid",)
        assert err[0]["type"] == "value_error.extra"

    def test_validate_environment(self, charm_exe):
        validator = self._plugin.validator_class(
            part_name="my-part", env=f"PATH={str(charm_exe.parent)}"
        )
        validator.validate_environment()

    def test_validate_environment_with_charm_part(self):
        validator = self._plugin.validator_class(part_name="my-part", env="PATH=/foo")
        validator.validate_environment(part_dependencies=["charm-tools"])

    def test_validate_missing_charm(self):
        validator = self._plugin.validator_class(part_name="my-part", env="/foo")
        with pytest.raises(PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == (
            "charm tool not found and part 'my-part' does "
            "not depend on a part named 'charm-tools'"
        )

    def test_validate_broken_charm(self, broken_charm_exe):
        validator = self._plugin.validator_class(
            part_name="my-part", env=f"PATH={str(broken_charm_exe.parent)}"
        )
        with pytest.raises(PluginEnvironmentValidationError) as raised:
            validator.validate_environment()

        assert raised.value.reason == "charm tools failed with error code 2"


@pytest.fixture
def build_dir(tmp_path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()

    return build_dir


@pytest.fixture
def install_dir(tmp_path):
    install_dir = tmp_path / "install"
    install_dir.mkdir()

    return install_dir


@pytest.fixture
def fake_run():
    patcher = patch("subprocess.run")
    yield patcher.start()
    patcher.stop()


def test_build(build_dir, install_dir, fake_run):
    reactive_plugin.build(charm_name="test-charm", build_dir=build_dir, install_dir=install_dir)

    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
        call(["charm", "build", "-o", build_dir], check=True),
    ]


def test_build_removes_charmcraft_yaml(build_dir, install_dir, fake_run):
    charmcraft_yaml = build_dir / "charmcraft.yaml"
    charmcraft_yaml.touch()

    reactive_plugin.build(charm_name="test-charm", build_dir=build_dir, install_dir=install_dir)

    assert not charmcraft_yaml.exists()
    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
        call(["charm", "build", "-o", build_dir], check=True),
    ]


def test_build_charm_proof_raises_error_messages(build_dir, install_dir, fake_run):
    fake_run.side_effect = CalledProcessError(200, "E: name missing")

    with pytest.raises(CalledProcessError):
        reactive_plugin.build(
            charm_name="test-charm", build_dir=build_dir, install_dir=install_dir
        )

    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
    ]


def test_build_charm_proof_raises_warning_messages_does_not_raise(
    build_dir, install_dir, fake_run
):
    fake_run.side_effect = CalledProcessError(100, "W: Description is not pretty")

    reactive_plugin.build(charm_name="test-charm", build_dir=build_dir, install_dir=install_dir)

    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
        call(["charm", "build", "-o", build_dir], check=True),
    ]


def test_build_charm_build_raises_error_messages(build_dir, install_dir, fake_run):
    fake_run.side_effect = [None, CalledProcessError(200, "E: name missing")]

    with pytest.raises(CalledProcessError):
        reactive_plugin.build(
            charm_name="test-charm", build_dir=build_dir, install_dir=install_dir
        )

    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
        call(["charm", "build", "-o", build_dir], check=True),
    ]


def test_build_charm_build_raises_warning_messages_does_not_raise(
    build_dir, install_dir, fake_run
):
    fake_run.side_effect = [None, CalledProcessError(100, "W: Description is not pretty")]

    reactive_plugin.build(charm_name="test-charm", build_dir=build_dir, install_dir=install_dir)

    assert not (build_dir / "test-charm").exists()
    assert fake_run.mock_calls == [
        call(["charm", "proof"], check=True),
        call(["charm", "build", "-o", build_dir], check=True),
    ]
