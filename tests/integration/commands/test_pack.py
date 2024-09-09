# Copyright 2024 Canonical Ltd.
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
import sys
import zipfile

import pytest
import yaml
from craft_application import util

from charmcraft import models, utils

CURRENT_PLATFORM = utils.get_os_platform()


@pytest.mark.xfail(
    sys.platform != "linux", reason="https://github.com/canonical/charmcraft/issues/1552"
)
@pytest.mark.parametrize(
    ("bundle_yaml", "filename"),
    [
        ("{}", "bundle.zip"),
        ("name: my-bundle", "my-bundle.zip"),
    ],
)
def test_build_basic_bundle(monkeypatch, capsys, app, new_path, bundle_yaml, filename):
    (new_path / "charmcraft.yaml").write_text("type: bundle")
    (new_path / "bundle.yaml").write_text(bundle_yaml)

    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr("sys.argv", ["charmcraft", "pack", "--verbosity=trace"])

    app.configure({})
    if app.run() != 0:
        raise ValueError(capsys.readouterr())

    with zipfile.ZipFile(filename) as bundle_zip:
        actual_bundle_yaml = bundle_zip.read("bundle.yaml").decode()

    assert actual_bundle_yaml == bundle_yaml


@pytest.mark.parametrize(
    ("charmcraft_project", "platform"),
    [
        pytest.param(
            {
                "type": "charm",
                "name": "my-charm",
                "summary": "A test charm",
                "description": "A charm for testing",
                "bases": [
                    {
                        "build-on": [{"name": "ubuntu", "channel": "22.04"}],
                        "run-on": [
                            {"name": "ubuntu", "channel": "22.04", "architectures": ["amd64"]}
                        ],
                    }
                ],
            },
            "ubuntu-22.04-amd64",
            marks=pytest.mark.skipif(
                CURRENT_PLATFORM.release != "22.04", reason="Bases charm only tested on jammy."
            ),
            id="bases-charm",
        ),
        pytest.param(
            {
                "type": "charm",
                "name": "my-charm",
                "summary": "A test charm",
                "description": "A charm for testing",
                "base": "ubuntu@22.04",
                "platforms": {
                    "ubuntu-22.04-amd64": {"build-on": ["amd64"], "build-for": ["amd64"]}
                },
                "parts": {},
            },
            "ubuntu-22.04-amd64",
            marks=pytest.mark.skipif(
                CURRENT_PLATFORM.release != "22.04", reason="Jammy charms only tested on jammy"
            ),
            id="platforms-jammy-charm",
        ),
        pytest.param(
            {
                "type": "charm",
                "name": "my-charm",
                "summary": "A test charm",
                "description": "A charm for testing",
                "base": "ubuntu@22.04",
                "platforms": {util.get_host_architecture(): None},
                "parts": {},
            },
            util.get_host_architecture(),
            marks=pytest.mark.skipif(
                CURRENT_PLATFORM.release != "22.04", reason="Jammy charms only tested on jammy"
            ),
            id="platforms-jammy-basic",
        ),
        pytest.param(
            {
                "type": "charm",
                "name": "my-charm",
                "summary": "A test charm",
                "description": "A charm for testing",
                "base": "ubuntu@24.04",
                "build-base": "ubuntu@devel",
                "platforms": {util.get_host_architecture(): None},
                "parts": {},
            },
            util.get_host_architecture(),
            marks=pytest.mark.skipif(
                CURRENT_PLATFORM.release != "24.04", reason="Noble charm needs noble"
            ),
            id="platforms-noble",
        ),
    ],
)
@pytest.mark.skipif(
    CURRENT_PLATFORM.system != "ubuntu",
    reason="Basic charm tests use destructive mode.",
)
def test_build_basic_charm(
    monkeypatch, emitter, new_path, charmcraft_project, service_factory, app, platform
):
    (new_path / "charmcraft.yaml").write_text(yaml.dump(charmcraft_project))
    service_factory.project = models.CharmcraftProject.unmarshal(charmcraft_project)

    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr(
        "sys.argv", ["charmcraft", "pack", "--destructive-mode", f"--platform={platform}"]
    )

    app.configure({})
    assert app.run() == 0

    with zipfile.ZipFile(new_path / f"my-charm_{platform}.charm") as charm_zip:
        metadata = yaml.safe_load(charm_zip.read("metadata.yaml"))
        manifest = yaml.safe_load(charm_zip.read("manifest.yaml"))

    emitter.assert_progress(f"Packing charm my-charm_{platform}.charm")

    assert "bases" in manifest
    if "platforms" in charmcraft_project:
        base_name = manifest["bases"][0]["name"]
        base_version = manifest["bases"][0]["channel"]
        assert f"{base_name}@{base_version}" == charmcraft_project["base"]
    else:
        assert manifest["bases"][0]["name"] in platform
        assert manifest["bases"][0]["channel"] in platform
    assert manifest["bases"][0]["architectures"][0] in platform

    assert metadata["name"] == charmcraft_project["name"]
    assert metadata["summary"] == charmcraft_project["summary"]
    assert metadata["description"] == charmcraft_project["description"]
