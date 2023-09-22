# Copyright 2023 Canonical Ltd.
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
"""Tests for package service."""
import sys
import zipfile
from textwrap import dedent

import pytest
import yaml

from charmcraft.config import load
from charmcraft.const import BUILD_DIRNAME
from charmcraft.models.charmcraft import Base, BasesConfiguration


@pytest.mark.parametrize(
    ("charmcraft_yaml", "metadata_yaml", "expected_zipname"),
    [
        [
            dedent(
                """\
                type: charm
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
            "test-charm-name-from-metadata-yaml_xname-xchannel-xarch1.charm",
        ],
        [
            dedent(
                """\
                name: test-charm-name-from-charmcraft-yaml
                type: charm
                summary: test summary
                description: test description
                """
            ),
            None,
            "test-charm-name-from-charmcraft-yaml_xname-xchannel-xarch1.charm",
        ],
    ],
)
def test_build_package_name(
    tmp_path,
    monkeypatch,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    expected_zipname,
    service_factory,
):
    """The zip file name comes from the config."""
    monkeypatch.chdir(tmp_path)
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)
    config = load(tmp_path)
    service_factory.project = config

    # zip it
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )

    zip_path = service_factory.package.pack_charm(to_be_zipped_dir, bases_config)

    assert zip_path == tmp_path / expected_zipname


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_package_tree_structure(monkeypatch, tmp_path, config, service_factory):
    """The zip file is properly built internally."""
    monkeypatch.chdir(tmp_path)
    # the metadata
    metadata_data = {"name": "test-charm-name-from-metadata-yaml"}
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wt", encoding="ascii") as fh:
        yaml.dump(metadata_data, fh)

    # create some dirs and files! a couple of files outside, and the dir we'll zip...
    file_outside_1 = tmp_path / "file_outside_1"
    with file_outside_1.open("wb") as fh:
        fh.write(b"content_out_1")
    file_outside_2 = tmp_path / "file_outside_2"
    with file_outside_2.open("wb") as fh:
        fh.write(b"content_out_2")
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # ...also outside a dir with a file...
    dir_outside = tmp_path / "extdir"
    dir_outside.mkdir()
    file_ext = dir_outside / "file_ext"
    with file_ext.open("wb") as fh:
        fh.write(b"external file")

    # ...then another file inside, and another dir...
    file_inside = to_be_zipped_dir / "file_inside"
    with file_inside.open("wb") as fh:
        fh.write(b"content_in")
    dir_inside = to_be_zipped_dir / "somedir"
    dir_inside.mkdir()

    # ...also inside, a link to the external dir...
    dir_linked_inside = to_be_zipped_dir / "linkeddir"
    dir_linked_inside.symlink_to(dir_outside)

    # ...and finally another real file, and two symlinks
    file_deep_1 = dir_inside / "file_deep_1"
    with file_deep_1.open("wb") as fh:
        fh.write(b"content_deep")
    file_deep_2 = dir_inside / "file_deep_2"
    file_deep_2.symlink_to(file_inside)
    file_deep_3 = dir_inside / "file_deep_3"
    file_deep_3.symlink_to(file_outside_1)

    # zip it
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )
    zip_path = service_factory.package.pack_charm(to_be_zipped_dir, bases_config)

    # check the stuff outside is not in the zip, the stuff inside is zipped (with
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zip_path)
    assert "file_outside_1" not in [x.filename for x in zf.infolist()]
    assert "file_outside_2" not in [x.filename for x in zf.infolist()]
    assert zf.read("file_inside") == b"content_in"
    assert zf.read("somedir/file_deep_1") == b"content_deep"  # own
    assert zf.read("somedir/file_deep_2") == b"content_in"  # from file inside
    assert zf.read("somedir/file_deep_3") == b"content_out_1"  # from file outside 1
    assert zf.read("linkeddir/file_ext") == b"external file"  # from file in the outside linked dir
