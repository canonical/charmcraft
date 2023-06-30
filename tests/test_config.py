# Copyright 2020-2022 Canonical Ltd.
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

import datetime
import os
import pathlib
import sys
from textwrap import dedent
from unittest.mock import patch

import pytest
from craft_cli import CraftError

from charmcraft import linters
from charmcraft.models.config import Base, BasesConfiguration, CharmhubConfig
from charmcraft.config import load
from charmcraft.utils import get_host_architecture


# -- tests for the config loading


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
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
        ],
    ],
)
def test_load_current_directory(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    monkeypatch,
):
    """Init the config using charmcraft.yaml in current directory."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    monkeypatch.chdir(tmp_path)
    fake_utcnow = datetime.datetime(1970, 1, 1, 0, 0, 2, tzinfo=datetime.timezone.utc)
    with patch("datetime.datetime") as mock:
        mock.utcnow.return_value = fake_utcnow
        config = load(None)
    assert config.type == "charm"
    assert config.project.dirpath == tmp_path
    assert config.project.config_provided
    assert config.project.started_at == fake_utcnow


def test_load_managed_mode_directory(monkeypatch, tmp_path):
    """Validate managed-mode default directory is /root/project."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")

    # Patch out Config (and Project) to prevent directory validation checks.
    with patch("charmcraft.config.Config"):
        with patch("charmcraft.config.Project") as mock_project:
            with patch("charmcraft.config.load_yaml"):
                load(None)

    assert mock_project.call_args.kwargs["dirpath"] == pathlib.Path("/root/project")


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
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
        ],
    ],
)
def test_load_specific_directory_ok(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Init the config using charmcraft.yaml in a specific directory."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


def test_load_optional_charmcraft_missing(tmp_path):
    """Specify a directory where the file is missing."""
    config = load(tmp_path)
    assert config.project.dirpath == tmp_path
    assert not config.project.config_provided


def test_load_optional_charmcraft_bad_directory(tmp_path):
    """Specify a missing directory."""
    missing_directory = tmp_path / "missing"
    config = load(missing_directory)
    assert config.project.dirpath == missing_directory
    assert not config.project.config_provided


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
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
        ],
    ],
)
def test_load_specific_directory_resolved(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    monkeypatch,
):
    """Ensure that the given directory is resolved to always show the whole path."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    # change to some dir, and reference the config dir relatively
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    config = load("../")

    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
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
        ],
    ],
)
@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_load_specific_directory_expanded(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    monkeypatch,
):
    """Ensure that the given directory is user-expanded."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    # fake HOME so the '~' indication is verified to work
    monkeypatch.setitem(os.environ, "HOME", str(tmp_path))
    config = load("~")

    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


# -- tests for schema restrictions


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                whatever: new-stuff
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_top_level_no_extra_properties(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """Schema validation, cannot add undefined properties at the top level."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'whatever' not permitted in top-level configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                charmhub:
                  api-url: https://www.canonical.com
                bases:
                  - build-on:
                      - name: test-build-name
                        channel: test-build-channel
                    run-on:
                      - name: test-build-name
                        channel: test-build-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_type_missing(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """Schema validation, type is mandatory."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'type' required in top-level configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: 33
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_type_bad_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, type is a string."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - must be either 'charm' or 'bundle' in field 'type'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: whatever
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_type_limited_values(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, type must be a subset of values."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - must be either 'charm' or 'bundle' in field 'type'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  api-url: 33
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_api_url_bad_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.api-url must be a string."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.api-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  api-url: stuff.com
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_api_url_bad_format(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.api-url must be a full URL."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.api-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  storage-url: 33
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_storage_url_bad_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.storage-url must be a string."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.storage-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  storage-url: stuff.com
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_storage_url_bad_format(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.storage-url must be a full URL."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.storage-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  registry-url: 33
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_registry_url_bad_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.registry-url must be a string."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.registry-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  registry-url: stuff.com
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_registry_url_bad_format(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, charmhub.registry-url must be a full URL."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.registry-url'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                charmhub:
                  storage-url: https://some.server.com
                  crazy: false
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_charmhub_no_extra_properties(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, cannot add undefined properties in charmhub key."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'crazy' not permitted in 'charmhub' configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts: ['foo', 'bar']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_init_structure(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad parts."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - value must be a dictionary in field 'parts'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  charm: ['foo', 'bar']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_bundle_structure(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad bundle."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - part 'charm' must be a dictionary in field 'parts'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  charm:
                    prime: foo
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_prime_structure(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad prime."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - value is not a valid list in field 'parts.charm.prime'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  charm:
                    prime: [{}, 'foo']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_prime_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with a prime holding not strings."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - string type expected in field 'parts.charm.prime[0]'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  charm:
                    prime: ['', 'foo']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_prime_type_empty(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with a prime holding not strings."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - path cannot be empty in field 'parts.charm.prime[0]'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  charm:
                    prime: ['/bar/foo', 'foo']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_basicprime_bad_content_format(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with a prime holding not strings."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - '/bar/foo' must be a relative path (cannot start with '/') in field 'parts.charm.prime[0]'"""  # NOQA: E501
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  other-part: 1
                  charm:
                    prime: ['/bar/foo', 'foo']
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_additional_part(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad part."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - part 'other-part' must be a dictionary in field 'parts'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:  # mandatory
                  - build-on:
                      - name: test-build-name
                        channel: test-build-channel
                    run-on:
                      - name: test-build-name
                        channel: test-build-channel
                parts:
                  other-part:
                    plugin: charm
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_other_charm_part_no_source(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad part."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'source' required in 'parts.other-part' configuration
        - cannot validate 'charm-requirements' because invalid 'source' configuration in field 'parts.other-part.charm-requirements'"""  # NOQA: E501
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                parts:
                  other-part:
                    plugin: bundle
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_other_bundle_part_no_source(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Schema validation, basic prime with bad part."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'source' required in 'parts.other-part' configuration"""
    )


# -- tests to check the double layer schema loading; using the 'charm' plugin
#    because it is the default (and has good default properties to be overriden and )
#    the 'dump' one because it's a special case of no having a model


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_no_parts_type_charm(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """No 'parts' specified at all, full default to charm plugin."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "charm",
            "source": str(tmp_path),
            "charm-binary-python-packages": [],
            "charm-entrypoint": "src/charm.py",
            "charm-python-packages": [],
            "charm-requirements": [],
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_no_parts_type_bundle(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """No 'parts' specified at all, full default to bundle plugin."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "bundle": {
            "plugin": "bundle",
            "source": str(tmp_path),
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  mycharm:
                    plugin: dump
                    source: https://the.net/whatever.tar.gz
                    source-type: tar
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_no_charm(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """The 'parts' key is specified, but no 'charm' entry."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "mycharm": {
            "plugin": "dump",
            "source": "https://the.net/whatever.tar.gz",
            "source-type": "tar",
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  charm:
                    prime: [to_be_included.*]  # random key to have a valid yaml
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_with_charm_plugin_missing(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """A charm part is specified but no plugin is indicated."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "charm",
            "source": str(tmp_path),
            "charm-binary-python-packages": [],
            "charm-entrypoint": "src/charm.py",
            "charm-python-packages": [],
            "charm-requirements": [],
            "prime": ["to_be_included.*"],
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  charm:
                    plugin: charm
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_with_charm_plugin_charm(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """A charm part is fully specified."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "charm",
            "source": str(tmp_path),
            "charm-binary-python-packages": [],
            "charm-entrypoint": "src/charm.py",
            "charm-python-packages": [],
            "charm-requirements": [],
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  charm:
                    plugin: dump
                    source: https://the.net/whatever.tar.gz
                    source-type: tar
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_with_charm_plugin_different(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """There is a 'charm' part but using a different plugin."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "dump",
            "source": "https://the.net/whatever.tar.gz",
            "source-type": "tar",
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  charm:
                    charm-entrypoint: different.py
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_with_charm_overriding_properties(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """A charm plugin is used and its default properties are overriden."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "charm",
            "source": str(tmp_path),
            "charm-binary-python-packages": [],
            "charm-entrypoint": "different.py",
            "charm-python-packages": [],
            "charm-requirements": [],
        }
    }


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: somebase
                    channel: "30.04"
                parts:
                  charm:
                    charm-point: different.py  # mispelled!
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_doublelayer_parts_with_charm_validating_props(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """A charm plugin is used and its validation schema is triggered ok."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'charm-point' not permitted in 'parts.charm' configuration"""
    )


# -- tests for Charmhub config


def test_charmhub_frozen():
    """Cannot change values from the charmhub config."""
    config = CharmhubConfig()
    with pytest.raises(TypeError):
        config.api_url = "broken"


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                charmhub:
                  storage_url: https://server1.com
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_charmhub_underscore_in_names(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Do not support underscore in attributes, only dash."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'storage_url' not permitted in 'charmhub' configuration"""
    )


# -- tests for bases


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_no_bases_is_ok_for_bundles(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Do not send a deprecation message if it is a bundle."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.type == "bundle"


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                bases:
                  - build-on:
                      - name: test-build-name
                        channel: test-build-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_forbidden_for_bundles(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Do not allow a bases configuration for bundles."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - Field not allowed when type=bundle in field 'bases'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-build-name
                        channel: test-build-channel
                    run-on:
                      - name: test-run-name
                        channel: test-run-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_minimal_long_form(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Minimal bases configuration, long form."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-build-name",
                        channel="test-build-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-run-name",
                        channel="test-run-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
            }
        )
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-name
                        channel: test-build-channel
                        extra-extra: read all about it
                    run-on:
                      - name: test-name
                        channel: test-run-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_extra_field_error(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Extra field in bases configuration."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'extra-extra' not permitted in 'bases[0].build-on[0]' configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build_on:
                      - name: test-name
                        channel: test-build-channel
                    run_on:
                      - name: test-name
                        channel: test-run-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_underscores_error(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'build-on' required in 'bases[0]' configuration
        - field 'run-on' required in 'bases[0]' configuration
        - extra field 'build_on' not permitted in 'bases[0]' configuration
        - extra field 'run_on' not permitted in 'bases[0]' configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-build-name
                        channel: 20.10
                    run-on:
                      - name: test-run-name
                        channel: test-run-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_channel_is_yaml_number(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - string type expected in field 'bases[0].build-on[0].channel'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-build-name
                        channel: test-build-channel
                    run-on:
                      - name: test-run-name
                        channel: test-run-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_minimal_long_form_bases(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-build-name",
                        channel="test-build-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-run-name",
                        channel="test-run-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
            }
        )
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-build-name-1
                        channel: test-build-channel-1
                      - name: test-build-name-2
                        channel: test-build-channel-2
                      - name: test-build-name-3
                        channel: test-build-channel-3
                        architectures: [riscVI]
                    run-on:
                      - name: test-run-name-1
                        channel: test-run-channel-1
                        architectures: [amd64]
                      - name: test-run-name-2
                        channel: test-run-channel-2
                        architectures: [amd64, arm64]
                      - name: test-run-name-3
                        channel: test-run-channel-3
                        architectures: [amd64, arm64, riscVI]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_complex_long_form_bases(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-build-name-1",
                        channel="test-build-channel-1",
                        architectures=[get_host_architecture()],
                    ),
                    Base(
                        name="test-build-name-2",
                        channel="test-build-channel-2",
                        architectures=[get_host_architecture()],
                    ),
                    Base(
                        name="test-build-name-3",
                        channel="test-build-channel-3",
                        architectures=["riscVI"],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-run-name-1",
                        channel="test-run-channel-1",
                        architectures=["amd64"],
                    ),
                    Base(
                        name="test-run-name-2",
                        channel="test-run-channel-2",
                        architectures=["amd64", "arm64"],
                    ),
                    Base(
                        name="test-run-name-3",
                        channel="test-run-channel-3",
                        architectures=["amd64", "arm64", "riscVI"],
                    ),
                ],
            }
        )
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: test-build-name-1
                        channel: test-build-channel-1
                    run-on:
                      - name: test-run-name-1
                        channel: test-run-channel-1
                        architectures: [amd64, arm64]
                  - build-on:
                      - name: test-build-name-2
                        channel: test-build-channel-2
                    run-on:
                      - name: test-run-name-2
                        channel: test-run-channel-2
                        architectures: [amd64, arm64]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_multiple_long_form_bases(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-build-name-1",
                        channel="test-build-channel-1",
                        architectures=[get_host_architecture()],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-run-name-1",
                        channel="test-run-channel-1",
                        architectures=["amd64", "arm64"],
                    ),
                ],
            }
        ),
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-build-name-2",
                        channel="test-build-channel-2",
                        architectures=[get_host_architecture()],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-run-name-2",
                        channel="test-run-channel-2",
                        architectures=["amd64", "arm64"],
                    ),
                ],
            }
        ),
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                    channel: test-channel
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_minimal_short_form(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
                "run-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    ),
                ],
            }
        )
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                    channel: test-channel
                    extra-extra: read all about it
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_short_form_extra_field_error(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - extra field 'extra-extra' not permitted in 'bases[0]' configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_short_form_missing_field_error(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'channel' required in 'bases[0]' configuration"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                  - build-on:
                      - name: test-build-name
                    run-on:
                      - name: test-run-name
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_bases_mixed_form_errors(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Only the short-form errors are exposed as its the first validation pass."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - field 'channel' required in 'bases[0]' configuration"""
    )


# -- tests for analysis


@pytest.fixture
def create_checker(monkeypatch):
    """Helper to patch and add checkers to the real structure."""
    test_checkers = []
    monkeypatch.setattr(linters, "CHECKERS", test_checkers)

    def add_checker(c_name, c_type):
        class FakeChecker:
            name = c_name
            check_type = c_type

        test_checkers.append(FakeChecker)

    return add_checker


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_missing(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """No analysis configuration leads to some defaults in place."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == []


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                analysis:
                  ignore:
                    attributes: []
                    linters: []
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_full_struct_just_empty(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """Complete analysis structure, empty."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == []


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                analysis:
                  ignore:
                    attributes: [check_ok_1, check_ok_2]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_ignore_attributes(
    tmp_path,
    create_checker,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """Some attributes are correctly ignored."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.attribute)
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.analysis.ignore.attributes == ["check_ok_1", "check_ok_2"]
    assert config.analysis.ignore.linters == []


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                analysis:
                  ignore:
                    linters: [check_ok_1, check_ok_2]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_ignore_linters(
    tmp_path,
    create_checker,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """Some linters are correctly ignored."""
    create_checker("check_ok_1", linters.CheckType.lint)
    create_checker("check_ok_2", linters.CheckType.lint)
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == ["check_ok_1", "check_ok_2"]


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                analysis:
                  ignore:
                    attributes: [check_ok_1, check_missing]
                    linters: [check_ok_2]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_ignore_attribute_missing(
    tmp_path,
    create_checker,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """An attribute specified to ignore is missing in the system."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.lint)
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - Bad attribute name 'check_missing' in field 'analysis.ignore.attributes[1]'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: bundle
                analysis:
                  ignore:
                    attributes: [check_ok_1]
                    linters: [check_ok_2, check_missing]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_schema_analysis_ignore_linter_missing(
    tmp_path,
    create_checker,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """A linter specified to ignore is missing in the system."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.lint)
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError) as cm:
        load(tmp_path)
    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - Bad lint name 'check_missing' in field 'analysis.ignore.linters[1]'"""
    )


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                    channel: test-channel
                actions:
                  pause:
                    description: Pause the database.
                  resume:
                    description: Resume a paused database.
                  snapshot:
                    description: Take a snapshot of the database.
                    params:
                      filename:
                        type: string
                        description: The name of the snapshot file.
                      compression:
                        type: object
                        description: The type of compression to use.
                        properties:
                          kind:
                            type: string
                            enum: [gzip, bzip2, xz]
                          quality:
                            description: Compression quality
                            type: integer
                            minimum: 0
                            maximum: 9
                    required: [filename]
                    additionalProperties: false
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_actions_defined_in_charmcraft_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml, charmcraft_yaml, metadata_yaml
):
    """test actions defined in charmcraft.yaml"""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(tmp_path)

    assert config.actions == {
        "pause": {"description": "Pause the database."},
        "resume": {"description": "Resume a paused database."},
        "snapshot": {
            "description": "Take a snapshot of the database.",
            "params": {
                "filename": {"type": "string", "description": "The name of the snapshot file."},
                "compression": {
                    "type": "object",
                    "description": "The type of compression to use.",
                    "properties": {
                        "kind": {"type": "string", "enum": ["gzip", "bzip2", "xz"]},
                        "quality": {
                            "description": "Compression quality",
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 9,
                        },
                    },
                },
            },
            "required": ["filename"],
            "additionalProperties": False,
        },
    }


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                    channel: test-channel
                actions:
                  pause:
                    description: Pause the database.
                  resume:
                    description: Resume a paused database.
                  {bad_name}:
                    description: Take a snapshot of the database.
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
@pytest.mark.parametrize(
    "bad_name",
    [
        "is",
        "-snapshot",
        "111snapshot",
    ],
)
def test_actions_badly_defined_in_charmcraft_yaml(
    tmp_path,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    bad_name,
):
    """test actions badly defined in charmcraft.yaml"""
    prepare_charmcraft_yaml(charmcraft_yaml_template.format(bad_name=bad_name))
    prepare_metadata_yaml(metadata_yaml)

    with pytest.raises(CraftError):
        load(tmp_path)


@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: test-name
                    channel: test-channel
                actions:
                  pause:
                    description: Pause the database.
                  resume:
                    description: Resume a paused database.
                  snapshot:
                    description: Take a snapshot of the database.
                    params:
                      filename:
                        type: string
                        description: The name of the snapshot file.
                      compression:
                        type: object
                        description: The type of compression to use.
                        properties:
                          kind:
                            type: string
                            enum: [gzip, bzip2, xz]
                          quality:
                            description: Compression quality
                            type: integer
                            minimum: 0
                            maximum: 9
                    required: [filename]
                    additionalProperties: false
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_actions_defined_in_charmcraft_yaml_and_actions_yaml(
    tmp_path,
    create_checker,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    prepare_actions_yaml,
    charmcraft_yaml,
    metadata_yaml,
):
    """actions section cannot be used when actions.yaml file is present."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)
    prepare_actions_yaml("test")

    with pytest.raises(CraftError) as cm:
        load(tmp_path)

    assert str(cm.value) == dedent(
        """\
        Bad charmcraft.yaml content:
        - 'actions.yaml' file not allowed when an 'actions' section is defined in 'charmcraft.yaml' in field 'actions'"""  # NOQA: E501
    )
