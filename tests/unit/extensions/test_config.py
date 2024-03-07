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
"""Unit tests for the config extension."""
import pathlib
import textwrap

import pytest

from charmcraft import const, errors, extensions


@pytest.fixture()
def extension():
    return extensions.Config(
        project_root=pathlib.Path("/root/project"), yaml_data={"type": "charm"}
    )


def test_get_supported_bases():
    assert extensions.Config.get_supported_bases() == sorted(const.SUPPORTED_BASES)


@pytest.mark.parametrize("base", [None, *const.SUPPORTED_BASES])
def test_is_experimental(base):
    assert not extensions.Config.is_experimental(base)


def test_get_root_snippet_fails_with_metadata_not_file(fs, extension):
    fs.create_dir("/root/project/metadata.yaml")

    with pytest.raises(errors.InvalidYamlFileError) as exc:
        extension.get_root_snippet()

    assert exc.value.resolution == "Ensure 'config.yaml' is a file"


@pytest.mark.parametrize("contents", ["", "[]", "Some text", None])
def test_get_root_snippet_fails_with_invalid_file(fs, extension, contents):
    fs.create_file("/root/project/config.yaml", contents=contents)

    with pytest.raises(errors.InvalidYamlFileError) as exc:
        extension.get_root_snippet()

    assert exc.value.resolution == "Ensure 'config.yaml' is a valid YAML dictionary"


@pytest.mark.parametrize(
    ("contents", "details"),
    [
        (
            textwrap.dedent(
                """\
                options:
                """
            ),
            "Duplicate fields: 'options'",
        )
    ],
)
def test_duplicate_fields(fs, contents, details):
    fs.create_file("/root/project/config.yaml", contents=contents)
    extension = extensions.Config(
        project_root=pathlib.Path("/root/project"), yaml_data={"options": None}
    )

    with pytest.raises(errors.CraftError) as exc:
        extension.get_root_snippet()

    assert exc.value.details == details


@pytest.mark.parametrize(
    ("metadata_yaml", "root_snippet"),
    [
        ("options:", {"config": {"options": None}},),
        ("{}", {"config": {}}),
        ("options: {my-option: {type: boolean}}", {"config": {"options": {"my-option": {"type": "boolean"}}}}),
    ],
)
def test_get_root_snippet_successful_load(fs, extension, metadata_yaml, root_snippet):
    fs.create_file("/root/project/config.yaml", contents=metadata_yaml)

    assert extension.get_root_snippet() == root_snippet


def test_get_part_snippet(extension):
    assert extension.get_part_snippet() == {}


def test_get_parts_snippet(extension):
    assert extension.get_parts_snippet() == {}
