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
import contextlib
import pathlib
import sys
import textwrap

import pyfakefs.fake_filesystem
import pytest

from charmcraft import application, errors


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
    with contextlib.suppress(FileExistsError):  # Exception occurs on Windows only.
        fs.create_dir(expected_project_dir)

    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    app.configure(global_args)

    assert app._work_dir == pathlib.Path(expected_project_dir).resolve()


@pytest.mark.parametrize(
    ("charmcraft_dict", "metadata_yaml"),
    [
        (
            {},
            textwrap.dedent("""\
                name: test-charm
                summary: A test charm
                description: A charm for testing!"""
            ),
        ),
        (
            {"name": "test-charm"},
            textwrap.dedent("""\
                summary: A test charm
                description: A charm for testing!"""
            ),
        ),
        (
            {"name": "test-charm", "summary": "A test charm"},
            textwrap.dedent("""\
                description: A charm for testing!"""
            ),
        ),
        (
            {"name": "test-charm", "summary": "A test charm", "description": "A charm for testing!"},
            textwrap.dedent("""\
                something-else: yes
                """
            ),
        ),

    ]
)
@pytest.mark.parametrize(
    "expected",
    [{"name": "test-charm", "summary": "A test charm", "description": "A charm for testing!"}],
)
def test_extra_yaml_transform_success(
    fs: pyfakefs.fake_filesystem.FakeFilesystem, service_factory, charmcraft_dict, metadata_yaml, expected
):
    """Test that _extra_yaml_transform correctly transforms the data."""
    fs.create_file("metadata.yaml", contents=metadata_yaml)
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    actual = app._extra_yaml_transform(charmcraft_dict)

    assert actual == expected


@pytest.mark.parametrize(
    ("charmcraft_dict", "metadata_yaml", "message"),
    [
        (
            {"name": "test-charm", "summary": "A test charm", "description": "A charm for testing!"},
            "",
            "Invalid file: 'metadata.yaml'",
        ),
        (
            {"name": "test-charm", "summary": "A test charm", "description": "A charm for testing!"},
            textwrap.dedent("""\
                name: test-charm
                summary: A test charm
                description: A charm for testing!"""
            ),
            "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
        )
    ],
)
def test_extra_yaml_transform_failure(
    fs: pyfakefs.fake_filesystem.FakeFilesystem, service_factory, charmcraft_dict, metadata_yaml, message
):
    fs.create_file("metadata.yaml", contents=metadata_yaml)
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)

    with pytest.raises(errors.CraftError) as exc_info:
        app._extra_yaml_transform(charmcraft_dict)

    assert exc_info.value.args[0] == message
