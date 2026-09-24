# Copyright 2024-2025 Canonical Ltd.
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
"""Integration tests for packing."""

import pathlib
import time
import zipfile
from unittest import mock

import craft_application
from craft_parts import callbacks
import craft_platforms
import pytest
import yaml
from craft_cli.pytest_plugin import RecordingEmitter

from charmcraft import application, const, services, utils
from charmcraft.application import commands
from charmcraft.application.main import Charmcraft

CURRENT_PLATFORM = utils.get_os_platform()


def _reset_parts_callbacks() -> None:
    """Reset craft-parts callback state between repeated app runs in one test."""
    callbacks.unregister_all()


def _state_dir_for(work_dir: pathlib.Path) -> pathlib.Path:
    """Return a state directory outside the work tree used for repeated pack tests."""
    return work_dir.parent / f"{work_dir.name}-state"


def _create_app(
    project_dir: pathlib.Path,
    work_dir: pathlib.Path,
    state_dir: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Charmcraft:
    services.register_services()
    service_factory = craft_application.ServiceFactory(app=application.APP_METADATA)
    service_factory.update_kwargs("charm_libs", project_dir=project_dir)
    service_factory.update_kwargs(
        "lifecycle",
        work_dir=work_dir,
        cache_dir="~/.cache",
    )
    service_factory.update_kwargs("project", project_dir=project_dir)
    service_factory.update_kwargs("provider", work_dir=work_dir)
    service_factory.get("project").configure(platform=None, build_for=None)
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CRAFT_STATE_DIR", str(state_dir))
    service_factory.get("state").set(
        "charmcraft", "started_at", value="2020-03-14T00:00:00+00:00", overwrite=True
    )
    app = application.Charmcraft(
        app=application.APP_METADATA,
        services=service_factory,
    )
    app._configure_services(None)
    app.services.get("store").client = mock.Mock()  # ty: ignore[unresolved-attribute]
    commands.fill_command_groups(app)
    return app


@pytest.mark.slow
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_build_basic_charm(
    monkeypatch: pytest.MonkeyPatch,
    emitter: RecordingEmitter,
    new_path: pathlib.Path,
    app: Charmcraft,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv",
        ["charmcraft", "pack", "--destructive-mode"],
    )
    (new_path / "requirements.txt").write_text(
        "distro==1.4.0"
    )  # Any requirement will do.

    app.configure({})
    assert app.run() == 0

    charm_files = list(new_path.glob("example-charm_*.charm"))
    assert len(charm_files) == 1

    with zipfile.ZipFile(charm_files[0]) as charm_zip:
        metadata = yaml.safe_load(charm_zip.read("metadata.yaml"))
        manifest = yaml.safe_load(charm_zip.read("manifest.yaml"))

    emitter.assert_progress(f"Packing charm {charm_files[0].name}")

    project = app.services.get("project").get().marshal()

    assert "bases" in manifest
    if "platforms" in project:
        base_name = manifest["bases"][0]["name"]
        base_version = manifest["bases"][0]["channel"]
        assert f"{base_name}@{base_version}" == project["base"]
    else:
        assert manifest["bases"][0]["name"] == CURRENT_PLATFORM.system
        assert manifest["bases"][0]["channel"] == CURRENT_PLATFORM.release
    assert (
        manifest["bases"][0]["architectures"][0]
        == craft_platforms.DebianArchitecture.from_host()
    )

    assert metadata["name"] == project["name"]
    assert metadata["summary"] == project["summary"]
    assert metadata["description"] == project["description"]


@pytest.mark.slow
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_pack_skips_when_inputs_are_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    emitter: RecordingEmitter,
    new_path: pathlib.Path,
    project_path: pathlib.Path,
    fake_project_file: pathlib.Path,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv",
        ["charmcraft", "pack", "--destructive-mode"],
    )
    (project_path / "requirements.txt").write_text("distro==1.4.0")
    state_dir = _state_dir_for(new_path)

    first_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    first_app.configure({})
    if first_app.run() != 0:
        pytest.skip("pack requires unavailable host build packages in this environment")

    charm_path = next(new_path.glob("example-charm_*.charm"))
    first_mtime_ns = charm_path.stat().st_mtime_ns

    time.sleep(1)
    _reset_parts_callbacks()

    second_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    second_app.configure({})
    assert second_app.run() == 0

    assert charm_path.stat().st_mtime_ns == first_mtime_ns
    emitter.assert_progress("Skipping pack (already ran)")


@pytest.mark.slow
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_pack_rebuilds_when_project_metadata_changes(
    monkeypatch: pytest.MonkeyPatch,
    emitter: RecordingEmitter,
    new_path: pathlib.Path,
    project_path: pathlib.Path,
    fake_project_file: pathlib.Path,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv",
        ["charmcraft", "pack", "--destructive-mode"],
    )
    (project_path / "requirements.txt").write_text("distro==1.4.0")
    state_dir = _state_dir_for(new_path)

    first_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    first_app.configure({})
    if first_app.run() != 0:
        pytest.skip("pack requires unavailable host build packages in this environment")

    charm_path = next(new_path.glob("example-charm_*.charm"))
    first_mtime_ns = charm_path.stat().st_mtime_ns

    time.sleep(1)
    (project_path / const.METADATA_FILENAME).write_text("subordinate: true\n")
    _reset_parts_callbacks()

    second_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    second_app.configure({})
    assert second_app.run() == 0

    assert charm_path.stat().st_mtime_ns > first_mtime_ns


@pytest.mark.slow
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_pack_artifact_contains_dispatch_after_repeated_pack(
    monkeypatch: pytest.MonkeyPatch,
    emitter: RecordingEmitter,
    new_path: pathlib.Path,
    project_path: pathlib.Path,
    fake_project_file: pathlib.Path,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv",
        ["charmcraft", "pack", "--destructive-mode"],
    )
    (project_path / "requirements.txt").write_text("distro==1.4.0")
    state_dir = _state_dir_for(new_path)

    first_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    first_app.configure({})
    if first_app.run() != 0:
        pytest.skip("pack requires unavailable host build packages in this environment")

    _reset_parts_callbacks()
    second_app = _create_app(project_path, new_path, state_dir, monkeypatch)
    second_app.configure({})
    assert second_app.run() == 0

    charm_path = next(new_path.glob("example-charm_*.charm"))
    with zipfile.ZipFile(charm_path) as charm_zip:
        assert const.DISPATCH_FILENAME in charm_zip.namelist()
