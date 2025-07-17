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
import zipfile

import craft_platforms
import pytest
import yaml
from craft_application import ServiceFactory
from craft_cli.pytest_plugin import RecordingEmitter

from charmcraft import utils
from charmcraft.application.main import Charmcraft

CURRENT_PLATFORM = utils.get_os_platform()


@pytest.mark.slow
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_build_basic_charm(
    monkeypatch: pytest.MonkeyPatch,
    emitter: RecordingEmitter,
    new_path: pathlib.Path,
    service_factory: ServiceFactory,
    app: Charmcraft,
):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv",
        ["charmcraft", "pack", "--destructive-mode"],
    )

    app.configure({})
    assert app.run() == 0

    charm_files = list(new_path.glob("example-charm_*.charm"))
    assert len(charm_files) == 1

    with zipfile.ZipFile(charm_files[0]) as charm_zip:
        metadata = yaml.safe_load(charm_zip.read("metadata.yaml"))
        manifest = yaml.safe_load(charm_zip.read("manifest.yaml"))

    emitter.assert_progress(f"Packing charm {charm_files[0].name}")

    assert "bases" in manifest
    project = app.services.get("project").get().marshal()
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
