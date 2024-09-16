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

import pytest
from craft_application import util

from charmcraft import utils


@pytest.mark.parametrize(
    "charm_dir",
    [
        pytest.param(path, id=path.name)
        for path in sorted((pathlib.Path(__file__).parent / "sample-charms").iterdir())
    ],
)
def test_load_charm(app, charm_dir):
    app.project_dir = charm_dir

    project = app.get_project()
    with (charm_dir / "expected.yaml").open() as f:
        expected_data = util.safe_yaml_load(f)

    project_dict = project.marshal()

    assert project_dict == expected_data
    assert utils.dump_yaml(project_dict) == (charm_dir / "expected.yaml").read_text()
