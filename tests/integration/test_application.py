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

import pathlib
import shutil

import pytest
from craft_application import util

from charmcraft import utils
from charmcraft.application.main import create_app


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
    app._configure_services(None)
    app.configure({})

    app.services.get("project").configure(platform=None, build_for=None)
    project = app.services.get("project").get()
    with (charm_dir / "expected.yaml").open() as f:
        expected_data = util.safe_yaml_load(f)

    project_dict = project.marshal()

    assert project_dict == expected_data
    assert utils.dump_yaml(project_dict) == (charm_dir / "expected.yaml").read_text()
