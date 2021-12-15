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

import craft_parts
import pydantic
import pytest
from craft_parts import plugins
from craft_parts.errors import PluginEnvironmentValidationError

from charmcraft.reactive_plugin import (
    ReactivePlugin,
    ReactivePluginProperties,
)

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
        plugin_properties = ReactivePluginProperties.unmarshal(spec)
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
            "rm -f charmcraft.yaml",
            # exit on errors (code 200), warnings (code 100) allowed
            'charm proof || test "$?" -ge 200 && exit 1',
            f'mkdir -p "{tmp_path}/parts/foo/install"',
            f'ln -sf . "{tmp_path}/parts/foo/install/fake-project"',
            f'charm build -o "{tmp_path}/parts/foo/install" || test "$?" -ge 200 && exit 1',
            f'rm -f "{tmp_path}/parts/foo/install/fake-project"',
        ]

    def test_invalid_properties(self):
        with pytest.raises(pydantic.ValidationError) as raised:
            ReactivePlugin.properties_class.unmarshal({"source": ".", "reactive-invalid": True})
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
