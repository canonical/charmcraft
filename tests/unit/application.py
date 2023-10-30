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
"""Unit tests for application class."""
import pathlib

import pyfakefs.fake_filesystem
import pytest

from charmcraft import application


@pytest.mark.parametrize(
    ("global_args", "expected_project_dir"),
    [
        ({"project_dir": "."}, "."),
        ({"project_dir": None}, "."),
        ({"project_dir": "/some/project/directory"}, "/some/project/directory"),
    ],
)
def test_configure(
    fs: pyfakefs.fake_filesystem.FakeFilesystem, service_factory, global_args, expected_project_dir
):
    fs.create_dir(expected_project_dir)

    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app.configure(global_args)

    assert app._work_dir == pathlib.Path(expected_project_dir).resolve()
