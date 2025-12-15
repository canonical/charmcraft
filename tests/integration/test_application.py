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
"""Integration tests for the Charmcraft class."""

import json
import pathlib
import shutil
from collections.abc import Iterator

import craft_parts
import pydantic
import pytest
from craft_application import util

from charmcraft import parts, utils
from charmcraft.application.main import create_app


@pytest.fixture(autouse=True)
def setup_parts() -> Iterator[None]:
    # Set us back to the default craft-parts plugins only
    craft_parts.plugins.unregister_all()
    yield
    # Teardown
    parts.setup_parts()


@pytest.mark.parametrize(
    "charm_dir",
    [
        pytest.param(path, id=path.name)
        for path in sorted((pathlib.Path(__file__).parent / "sample-charms").iterdir())
    ],
)
def test_load_charm(in_project_path, charm_dir):
    shutil.copytree(charm_dir, in_project_path, dirs_exist_ok=True)

    app = create_app()
    app._configure_early_services()
    app._initialize_craft_parts()
    app._configure_services(None)
    app.configure({})

    app.services.get("project").configure(platform=None, build_for=None)
    project = app.services.get("project").get()
    with (charm_dir / "expected.yaml").open() as f:
        expected_data = util.safe_yaml_load(f)

    project_dict = project.marshal()

    assert project_dict == expected_data
    assert utils.dump_yaml(project_dict) == (charm_dir / "expected.yaml").read_text()

    # Check that all the necessary plugins are registered.
    app._initialize_craft_parts()
    plugins = {v.get("plugin", k) for k, v in project.parts.items()}
    for plugin in plugins:
        craft_parts.plugins.get_plugin_class(plugin)


@pytest.mark.parametrize(
    "charm_dir",
    [
        pytest.param(path, id=path.name)
        for path in sorted((pathlib.Path(__file__).parent / "invalid-charms").iterdir())
    ],
)
def test_load_invalid_charm(in_project_path: pathlib.Path, charm_dir: pathlib.Path):
    shutil.copytree(charm_dir, in_project_path, dirs_exist_ok=True)

    app = create_app()
    app._configure_early_services()
    app._configure_services(None)
    app.configure({})

    app.services.get("project").configure(platform=None, build_for=None)
    with pytest.raises(pydantic.ValidationError) as exc_info:
        app.services.get("project").get()

    expected_exc_list = json.loads((charm_dir / "errors.json").read_text())

    # The Pydantic errors include a URL that includes the current Pydantic version,
    # meaning it changes in ways that aren't meaningful to test
    # Instead, just omit the URL from the test entirely.
    exc_list = json.loads(exc_info.value.json())
    for e in exc_list:
        _ = e.pop("url")

    assert exc_list == expected_exc_list, "Errors do not match"


@pytest.mark.parametrize(
    "charm_dir",
    [
        pytest.param(path, id=path.name)
        for path in sorted((pathlib.Path(__file__).parent / "invalid-charms").iterdir())
        if "charm-plugin" in path.name or "reactive-plugin" in path.name
    ],
)
def test_remove_charm_reactive_plugins(
    in_project_path: pathlib.Path, charm_dir: pathlib.Path
):
    shutil.copytree(charm_dir, in_project_path, dirs_exist_ok=True)

    app = create_app()
    app._configure_early_services()
    app._configure_services(None)
    app.configure({})

    # Test that we have not registered plugins that we didn't
    app._initialize_craft_parts()

    with pytest.raises(ValueError, match="plugin not registered: 'charm'"):
        craft_parts.plugins.plugins.get_plugin_class("charm")
    with pytest.raises(ValueError, match="plugin not registered: 'reactive'"):
        craft_parts.plugins.plugins.get_plugin_class("reactive")
