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

import pathlib
import sys
from unittest.mock import ANY, call, patch

import pydantic
import pytest
from craft_cli import CraftError
from craft_parts import Action, ActionType, Step
from craft_parts.errors import PartsError

from charmcraft import parts

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")


# -- tests for parts lifecycle


def test_partslifecycle_bad_bootstrap(tmp_path):
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


def test_partslifecycle_prime_dir(tmp_path):
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


def test_partslifecycle_run_new_entrypoint(tmp_path, monkeypatch):
    data = {
        "plugin": "charm",
        "source": ".",
        "charm-entrypoint": "my-entrypoint",
        "charm-python-packages": ["pkg1", "pkg2"],
        "charm-requirements": [],
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


def test_partslifecycle_run_same_entrypoint(tmp_path, monkeypatch):
    data = {
        "plugin": "charm",
        "source": ".",
        "charm-entrypoint": "src/charm.py",
        "charm-python-packages": ["pkg1", "pkg2"],
        "charm-requirements": [],
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


def test_partslifecycle_run_no_previous_entrypoint(tmp_path, monkeypatch):
    data = {
        "plugin": "charm",
        "source": ".",
        "charm-entrypoint": "my-entrypoint",
        "charm-python-packages": ["pkg1", "pkg2"],
        "charm-requirements": [],
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


def test_partslifecycle_run_actions_progress(tmp_path, monkeypatch, emitter):
    data = {
        "plugin": "nil",
        "source": ".",
    }

    lifecycle = parts.PartsLifecycle(
        all_parts={"testpart": data},
        work_dir=tmp_path,
        project_dir=tmp_path,
        project_name="test",
        ignore_local_sources=[],
    )

    action1 = Action(
        part_name="testpart", step=Step.STAGE, action_type=ActionType.RUN, reason=None
    )
    action2 = Action(
        part_name="testpart", step=Step.PRIME, action_type=ActionType.RUN, reason=None
    )

    with patch("craft_parts.LifecycleManager.plan") as mock_plan:
        mock_plan.return_value = [action1, action2]
        with patch("craft_parts.executor.executor.ExecutionContext.execute") as mock_exec:
            lifecycle.run(Step.PRIME)

    emitter.assert_progress("Running step STAGE for part 'testpart'")
    emitter.assert_progress("Running step PRIME for part 'testpart'")
    assert mock_exec.call_args_list == [
        call([action1], stdout=ANY, stderr=ANY),
        call([action2], stdout=ANY, stderr=ANY),
    ]


# -- tests for part helpers


def test_parthelpers_get_dispatch_entrypoint(tmp_path):
    dispatch = tmp_path / "dispatch"
    dispatch.write_text(
        'JUJU_DISPATCH_PATH="${JUJU_DISPATCH_PATH:-$0}" PYTHONPATH=lib:venv ./my/entrypoint'
    )
    entrypoint = parts._get_dispatch_entrypoint(tmp_path)
    assert entrypoint == "./my/entrypoint"


def test_parthelpers_get_dispatch_entrypoint_no_file(tmp_path):
    entrypoint = parts._get_dispatch_entrypoint(tmp_path)
    assert entrypoint == ""


# -- tests for part config processing


@pytest.mark.usefixtures("new_path")
def test_partconfig_happy_validation_and_completion():
    data = {
        "plugin": "charm",
        "source": ".",
    }
    completed = parts.process_part_config(data)
    assert completed == {
        "plugin": "charm",
        "source": ".",
        "charm-binary-python-packages": [],
        "charm-entrypoint": "src/charm.py",
        "charm-python-packages": [],
        "charm-requirements": [],
        "charm-strict-dependencies": False,
    }


def test_partconfig_no_plugin():
    data = {
        "source": ".",
    }
    with pytest.raises(ValueError) as raised:
        parts.process_part_config(data)
    assert str(raised.value) == "'plugin' not defined"


def test_partconfig_bad_property():
    data = {
        "plugin": "charm",
        "source": ".",
        "color": "purple",
    }
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.process_part_config(data)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("color",)
    assert err[0]["msg"] == "extra fields not permitted"


def test_partconfig_bad_type():
    data = {
        "plugin": "charm",
        "source": ["."],
    }
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.process_part_config(data)
    err = raised.value.errors()
    assert len(err) == 2
    assert err[0]["loc"] == ("source",)
    assert err[0]["msg"] == "str type expected"
    assert err[1]["loc"] == ("charm-requirements",)
    assert (
        err[1]["msg"]
        == "cannot validate 'charm-requirements' because invalid 'source' configuration"
    )


def test_partconfig_bad_plugin_property():
    data = {
        "plugin": "charm",
        "charm-timeout": "never",
        "source": ".",
    }
    with pytest.raises(pydantic.ValidationError) as raised:
        parts.process_part_config(data)
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("charm-timeout",)
    assert err[0]["msg"] == "extra fields not permitted"
