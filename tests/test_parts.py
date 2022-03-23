# Copyright 2020-2021 Canonical Ltd.
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
from unittest.mock import patch, call

import craft_parts
import pydantic
import pytest
from craft_cli import CraftError
from craft_parts import Step, plugins, Action, ActionType
from craft_parts.errors import PartsError

from charmcraft import charm_builder, parts


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")


class TestCharmPlugin:
    """Ensure plugin methods return expected data."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, tmp_path):
        project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
        spec = {
            "plugin": "charm",
            "source": str(tmp_path),
            "charm-entrypoint": "entrypoint",
            "charm-binary-python-packages": ["pkg1", "pkg2"],
            "charm-python-packages": ["pkg3", "pkg4"],
            "charm-requirements": ["reqs1.txt", "reqs2.txt"],
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

        self._plugin = plugins.get_plugin(
            part=part,
            part_info=part_info,
            properties=plugin_properties,
        )

    def test_get_build_package(self):
        assert self._plugin.get_build_packages() == {
            "python3-pip",
            "python3-setuptools",
            "python3-wheel",
            "python3-venv",
            "python3-dev",
        }

    def test_get_build_snaps(self):
        assert self._plugin.get_build_snaps() == set()

    def test_get_build_environment(self):
        assert self._plugin.get_build_environment() == {}

    def test_get_build_commands(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", "/some/path")
        monkeypatch.setenv("SNAP", "snap_value")
        monkeypatch.setenv("SNAP_ARCH", "snap_arch_value")
        monkeypatch.setenv("SNAP_NAME", "snap_name_value")
        monkeypatch.setenv("SNAP_VERSION", "snap_version_value")
        monkeypatch.setenv("http_proxy", "http_proxy_value")
        monkeypatch.setenv("https_proxy", "https_proxy_value")
        monkeypatch.setenv("no_proxy", "no_proxy_value")

        assert self._plugin.get_build_commands() == [
            "env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/some/path SNAP=snap_value "
            "SNAP_ARCH=snap_arch_value SNAP_NAME=snap_name_value "
            "SNAP_VERSION=snap_version_value http_proxy=http_proxy_value "
            "https_proxy=https_proxy_value no_proxy=no_proxy_value "
            "{python} -I "
            "{charm_builder} "
            "--charmdir {work_dir}/parts/foo/build "
            "--builddir {work_dir}/parts/foo/install "
            "--entrypoint {work_dir}/parts/foo/build/entrypoint "
            "-b pkg1 "
            "-b pkg2 "
            "-p pkg3 "
            "-p pkg4 "
            "-r reqs1.txt "
            "-r reqs2.txt".format(
                python=sys.executable,
                charm_builder=charm_builder.__file__,
                work_dir=str(tmp_path),
            )
        ]

    def test_invalid_properties(self):
        with pytest.raises(pydantic.ValidationError) as raised:
            parts.CharmPlugin.properties_class.unmarshal({"source": ".", "charm-invalid": True})
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("charm-invalid",)
        assert err[0]["type"] == "value_error.extra"


class TestBundlePlugin:
    """Ensure plugin methods return expected data."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, tmp_path):
        project_dirs = craft_parts.ProjectDirs(work_dir=tmp_path)
        spec = {
            "plugin": "bundle",
            "source": str(tmp_path),
        }
        plugin_properties = parts.BundlePluginProperties.unmarshal(spec)
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
        if sys.platform == "linux":
            assert self._plugin.get_build_commands() == [
                f'mkdir -p "{str(tmp_path)}/parts/foo/install"',
                f'cp --archive --link --no-dereference * "{str(tmp_path)}/parts/foo/install"',
            ]
        else:
            assert self._plugin.get_build_commands() == [
                f'mkdir -p "{str(tmp_path)}/parts/foo/install"',
                f'cp -R -p -P * "{str(tmp_path)}/parts/foo/install"',
            ]

    def test_invalid_properties(self):
        with pytest.raises(pydantic.ValidationError) as raised:
            parts.BundlePlugin.properties_class.unmarshal({"source": ".", "bundle-invalid": True})
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("bundle-invalid",)
        assert err[0]["type"] == "value_error.extra"


class TestPartsLifecycle:
    """Ensure parts data correctly used in lifecycle."""

    def test_bad_bootstrap(self, tmp_path):
        fake_error = PartsError("pumba")
        with patch("craft_parts.LifecycleManager.__init__") as mock:
            mock.side_effect = fake_error
            with pytest.raises(CraftError) as cm:
                parts.PartsLifecycle(
                    all_parts={},
                    work_dir="/some/workdir",
                    project_dir=tmp_path,
                    project_name="test",
                    ignore_local_sources=["*.charm"],
                )
            exc = cm.value
            assert str(exc) == "Error bootstrapping lifecycle manager: pumba"
            assert exc.__cause__ == fake_error

    def test_prime_dir(self, tmp_path):
        data = {
            "plugin": "charm",
            "source": ".",
        }

        with patch("craft_parts.LifecycleManager.refresh_packages_list"):
            lifecycle = parts.PartsLifecycle(
                all_parts={"charm": data},
                work_dir="/some/workdir",
                project_dir=tmp_path,
                project_name="test",
                ignore_local_sources=["*.charm"],
            )
        assert lifecycle.prime_dir == pathlib.Path("/some/workdir/prime")

    def test_run_new_entrypoint(self, tmp_path, monkeypatch):
        data = {
            "plugin": "charm",
            "source": ".",
            "charm-entrypoint": "my-entrypoint",
            "charm-python-packages": ["pkg1", "pkg2"],
            "charm-requirements": ["reqs1.txt", "reqs2.txt"],
        }

        # create dispatcher from previous run
        prime_dir = tmp_path / "prime"
        prime_dir.mkdir()
        dispatch = prime_dir / "dispatch"
        dispatch.write_text(
            'JUJU_DISPATCH_PATH="${JUJU_DISPATCH_PATH:-$0}" PYTHONPATH=lib:venv ./src/charm.py'
        )

        lifecycle = parts.PartsLifecycle(
            all_parts={"charm": data},
            work_dir=tmp_path,
            project_dir=tmp_path,
            project_name="test",
            ignore_local_sources=["*.charm"],
        )

        with patch("craft_parts.LifecycleManager.clean") as mock_clean:
            with patch("craft_parts.LifecycleManager.plan") as mock_plan:
                mock_plan.side_effect = SystemExit("test")
                with pytest.raises(SystemExit, match="test"):
                    lifecycle.run(Step.PRIME)

        mock_clean.assert_called_once_with(Step.BUILD, part_names=["charm"])

    def test_run_same_entrypoint(self, tmp_path, monkeypatch):
        data = {
            "plugin": "charm",
            "source": ".",
            "charm-entrypoint": "src/charm.py",
            "charm-python-packages": ["pkg1", "pkg2"],
            "charm-requirements": ["reqs1.txt", "reqs2.txt"],
        }

        # create dispatcher from previous run
        prime_dir = tmp_path / "prime"
        prime_dir.mkdir()
        dispatch = prime_dir / "dispatch"
        dispatch.write_text(
            'JUJU_DISPATCH_PATH="${JUJU_DISPATCH_PATH:-$0}" PYTHONPATH=lib:venv ./src/charm.py'
        )

        lifecycle = parts.PartsLifecycle(
            all_parts={"charm": data},
            work_dir=tmp_path,
            project_dir=tmp_path,
            project_name="test",
            ignore_local_sources=["*.charm"],
        )

        with patch("craft_parts.LifecycleManager.clean") as mock_clean:
            with patch("craft_parts.LifecycleManager.plan") as mock_plan:
                mock_plan.side_effect = SystemExit("test")
                with pytest.raises(SystemExit, match="test"):
                    lifecycle.run(Step.PRIME)

        mock_clean.assert_not_called()

    def test_run_no_previous_entrypoint(self, tmp_path, monkeypatch):
        data = {
            "plugin": "charm",
            "source": ".",
            "charm-entrypoint": "my-entrypoint",
            "charm-python-packages": ["pkg1", "pkg2"],
            "charm-requirements": ["reqs1.txt", "reqs2.txt"],
        }

        lifecycle = parts.PartsLifecycle(
            all_parts={"charm": data},
            work_dir=tmp_path,
            project_dir=tmp_path,
            project_name="test",
            ignore_local_sources=["*.charm"],
        )

        with patch("craft_parts.LifecycleManager.clean") as mock_clean:
            with patch("craft_parts.LifecycleManager.plan") as mock_plan:
                mock_plan.side_effect = SystemExit("test")
                with pytest.raises(SystemExit, match="test"):
                    lifecycle.run(Step.PRIME)

        mock_clean.assert_called_once_with(Step.BUILD, part_names=["charm"])

    def test_run_actions_progress(self, tmp_path, monkeypatch, emitter):
        data = {
            "plugin": "charm",
            "source": ".",
            "charm-entrypoint": "my-entrypoint",
        }

        lifecycle = parts.PartsLifecycle(
            all_parts={"charm": data},
            work_dir=tmp_path,
            project_dir=tmp_path,
            project_name="test",
            ignore_local_sources=["*.charm"],
        )

        action1 = Action(
            part_name="charm", step=Step.STAGE, action_type=ActionType.RUN, reason=None
        )
        action2 = Action(
            part_name="charm", step=Step.PRIME, action_type=ActionType.RUN, reason=None
        )

        with patch("craft_parts.LifecycleManager.clean"):
            with patch("craft_parts.LifecycleManager.plan") as mock_plan:
                mock_plan.return_value = [action1, action2]
                with patch("craft_parts.executor.executor.ExecutionContext.execute") as mock_exec:
                    lifecycle.run(Step.PRIME)

        emitter.assert_progress("Running step STAGE for part 'charm'")
        emitter.assert_progress("Running step PRIME for part 'charm'")
        assert mock_exec.call_args_list == [
            call([action1]),
            call([action2]),
        ]


class TestPartHelpers:
    """Verify helper functions."""

    def test_get_dispatch_entrypoint(self, tmp_path):
        dispatch = tmp_path / "dispatch"
        dispatch.write_text(
            'JUJU_DISPATCH_PATH="${JUJU_DISPATCH_PATH:-$0}" PYTHONPATH=lib:venv ./my/entrypoint'
        )
        entrypoint = parts._get_dispatch_entrypoint(tmp_path)
        assert entrypoint == "./my/entrypoint"

    def test_get_dispatch_entrypoint_no_file(self, tmp_path):
        entrypoint = parts._get_dispatch_entrypoint(tmp_path)
        assert entrypoint == ""


class TestPartValidation:
    """Part data validation scenarios."""

    def test_part_validation_happy(self):
        data = {
            "plugin": "charm",
            "source": ".",
        }
        parts.validate_part(data)

    def test_part_validation_no_plugin(self):
        data = {
            "source": ".",
        }
        with pytest.raises(ValueError) as raised:
            parts.validate_part(data)
        assert str(raised.value) == "'plugin' not defined"

    def test_part_validation_bad_property(self):
        data = {
            "plugin": "charm",
            "source": ".",
            "color": "purple",
        }
        with pytest.raises(pydantic.ValidationError) as raised:
            parts.validate_part(data)
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("color",)
        assert err[0]["msg"] == "extra fields not permitted"

    def test_part_validation_bad_type(self):
        data = {
            "plugin": "charm",
            "source": ["."],
        }
        with pytest.raises(pydantic.ValidationError) as raised:
            parts.validate_part(data)
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("source",)
        assert err[0]["msg"] == "str type expected"

    def test_part_validation_bad_plugin_property(self):
        data = {
            "plugin": "charm",
            "charm-timeout": "never",
            "source": ".",
        }
        with pytest.raises(pydantic.ValidationError) as raised:
            parts.validate_part(data)
        err = raised.value.errors()
        assert len(err) == 1
        assert err[0]["loc"] == ("charm-timeout",)
        assert err[0]["msg"] == "extra fields not permitted"
