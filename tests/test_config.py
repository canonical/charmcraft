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
from charmcraft import linters
from charmcraft.config import Base, BasesConfiguration, CharmhubConfig, load
from charmcraft.utils import get_host_architecture
from craft_cli import CraftError

# -- tests for the config loading


def test_load_current_directory(create_config, monkeypatch):
    """Init the config using charmcraft.yaml in current directory."""
    tmp_path = create_config()
    monkeypatch.chdir(tmp_path)
    fake_utcnow = datetime.datetime(1970, 1, 1, 0, 0, 2, tzinfo=datetime.timezone.utc)
    with patch("datetime.datetime") as mock:
        mock.utcnow.return_value = fake_utcnow
        config = load(None)
    assert config.type == "charm"
    assert config.project.dirpath == tmp_path
    assert config.project.config_provided
    assert config.project.started_at == fake_utcnow


def test_load_managed_mode_directory(create_config, monkeypatch, tmp_path):
    """Validate managed-mode default directory is /root/project."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")

    # Patch out Config (and Project) to prevent directory validation checks.
    with patch("charmcraft.config.Config"):
        with patch("charmcraft.config.Project") as mock_project:
            with patch("charmcraft.config.load_yaml"):
                load(None)

    assert mock_project.call_args.kwargs["dirpath"] == pathlib.Path("/root/project")


def test_load_specific_directory_ok(create_config):
    """Init the config using charmcraft.yaml in a specific directory."""
    tmp_path = create_config()
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


def test_load_specific_directory_resolved(create_config, monkeypatch):
    """Ensure that the given directory is resolved to always show the whole path."""
    tmp_path = create_config()
    # change to some dir, and reference the config dir relatively
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    config = load("../")

    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_load_specific_directory_expanded(create_config, monkeypatch):
    """Ensure that the given directory is user-expanded."""
    tmp_path = create_config()
    # fake HOME so the '~' indication is verified to work
    monkeypatch.setitem(os.environ, "HOME", str(tmp_path))
    config = load("~")

    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


# -- tests for schema restrictions


@pytest.fixture
def check_schema_error(tmp_path):
    """Helper to check the schema error."""

    def check_schema_error(expected_msg):
        """The real checker."""
        with pytest.raises(CraftError) as cm:
            load(tmp_path)
        assert str(cm.value) == dedent(expected_msg)

    return check_schema_error


def test_schema_top_level_no_extra_properties(create_config, check_schema_error):
    """Schema validation, cannot add undefined properties at the top level."""
    create_config(
        """
        type: bundle
        whatever: new-stuff
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - extra field 'whatever' not permitted in top-level configuration"""
    )


def test_schema_type_missing(create_config, check_schema_error):
    """Schema validation, type is mandatory."""
    create_config(
        """
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
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - field 'type' required in top-level configuration"""
    )


def test_schema_type_bad_type(create_config, check_schema_error):
    """Schema validation, type is a string."""
    create_config(
        """
        type: 33
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - must be either 'charm' or 'bundle' in field 'type'"""
    )


def test_schema_type_limited_values(create_config, check_schema_error):
    """Schema validation, type must be a subset of values."""
    create_config(
        """
        type: whatever
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - must be either 'charm' or 'bundle' in field 'type'"""
    )


def test_schema_charmhub_api_url_bad_type(create_config, check_schema_error):
    """Schema validation, charmhub.api-url must be a string."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            api-url: 33
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.api-url'"""
    )


def test_schema_charmhub_api_url_bad_format(create_config, check_schema_error):
    """Schema validation, charmhub.api-url must be a full URL."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            api-url: stuff.com
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.api-url'"""
    )


def test_schema_charmhub_storage_url_bad_type(create_config, check_schema_error):
    """Schema validation, charmhub.storage-url must be a string."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            storage-url: 33
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.storage-url'"""
    )


def test_schema_charmhub_storage_url_bad_format(create_config, check_schema_error):
    """Schema validation, charmhub.storage-url must be a full URL."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            storage-url: stuff.com
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.storage-url'"""
    )


def test_schema_charmhub_registry_url_bad_type(create_config, check_schema_error):
    """Schema validation, charmhub.registry-url must be a string."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            registry-url: 33
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.registry-url'"""
    )


def test_schema_charmhub_registry_url_bad_format(create_config, check_schema_error):
    """Schema validation, charmhub.registry-url must be a full URL."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            registry-url: stuff.com
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - invalid or missing URL scheme in field 'charmhub.registry-url'"""
    )


def test_schema_charmhub_no_extra_properties(create_config, check_schema_error):
    """Schema validation, cannot add undefined properties in charmhub key."""
    create_config(
        """
        type: bundle
        charmhub:
            storage-url: https://some.server.com
            crazy: false
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - extra field 'crazy' not permitted in 'charmhub' configuration"""
    )


def test_schema_basicprime_bad_init_structure(create_config, check_schema_error):
    """Schema validation, basic prime with bad parts."""
    create_config(
        """
        type: bundle  # mandatory
        parts: ['foo', 'bar']
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - value must be a dictionary in field 'parts'"""
    )


def test_schema_basicprime_bad_bundle_structure(create_config, check_schema_error):
    """Instantiate charmhub using a bad structure."""
    """Schema validation, basic prime with bad bundle."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            charm: ['foo', 'bar']
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - part 'charm' must be a dictionary in field 'parts'"""
    )


def test_schema_basicprime_bad_prime_structure(create_config, check_schema_error):
    """Schema validation, basic prime with bad prime."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            charm:
                prime: foo
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - value is not a valid list in field 'parts.charm.prime'"""
    )


def test_schema_basicprime_bad_prime_type(create_config, check_schema_error):
    """Schema validation, basic prime with a prime holding not strings."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            charm:
                prime: [{}, 'foo']
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - string type expected in field 'parts.charm.prime[0]'"""
    )


def test_schema_basicprime_bad_prime_type_empty(create_config, check_schema_error):
    """Schema validation, basic prime with a prime holding not strings."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            charm:
                prime: ['', 'foo']
    """
    )
    check_schema_error(
        ("Bad charmcraft.yaml content:\n" "- path cannot be empty in field 'parts.charm.prime[0]'")
    )


def test_schema_basicprime_bad_content_format(create_config, check_schema_error):
    """Schema validation, basic prime with a prime holding not strings."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            charm:
                prime: ['/bar/foo', 'foo']
    """
    )
    check_schema_error(
        (
            "Bad charmcraft.yaml content:\n"
            "- '/bar/foo' must be a relative path (cannot start with '/')"
            " in field 'parts.charm.prime[0]'"
            ""
        )
    )


def test_schema_additional_part(create_config, check_schema_error):
    """Schema validation, basic prime with bad part."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            other-part: 1
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - part 'other-part' must be a dictionary in field 'parts'"""
    )


def test_schema_other_charm_part_no_source(create_config, check_schema_error):
    """Schema validation, basic prime with bad part."""
    create_config(
        """
        type: charm  # mandatory
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
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - field 'source' required in 'parts.other-part' configuration
        - cannot validate 'charm-requirements' because invalid 'source' configuration in field 'parts.other-part.charm-requirements'"""  # noqa: E501
    )


def test_schema_other_bundle_part_no_source(create_config, check_schema_error):
    """Schema validation, basic prime with bad part."""
    create_config(
        """
        type: bundle  # mandatory
        parts:
            other-part:
                plugin: bundle
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - field 'source' required in 'parts.other-part' configuration"""
    )


# -- tests to check the double layer schema loading; using the 'charm' plugin
#    because it is the default (and has good default properties to be overridden and )
#    the 'dump' one because it's a special case of no having a model


def test_schema_doublelayer_no_parts_type_charm(create_config):
    """No 'parts' specified at all, full default to charm plugin."""
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: somebase
            channel: "30.04"
    """
    )
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


def test_schema_doublelayer_no_parts_type_bundle(create_config):
    """No 'parts' specified at all, full default to bundle plugin."""
    tmp_path = create_config(
        """
        type: bundle
    """
    )
    config = load(tmp_path)
    assert config.parts == {
        "bundle": {
            "plugin": "bundle",
            "source": str(tmp_path),
        }
    }


def test_schema_doublelayer_parts_no_charm(create_config):
    """The 'parts' key is specified, but no 'charm' entry."""
    tmp_path = create_config(
        """
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
    )
    config = load(tmp_path)
    assert config.parts == {
        "mycharm": {
            "plugin": "dump",
            "source": "https://the.net/whatever.tar.gz",
            "source-type": "tar",
        }
    }


def test_schema_doublelayer_parts_with_charm_plugin_missing(create_config):
    """A charm part is specified but no plugin is indicated."""
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: somebase
            channel: "30.04"
        parts:
          charm:
            prime: [to_be_included.*]  # random key to have a valid yaml
    """
    )
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


def test_schema_doublelayer_parts_with_charm_plugin_charm(create_config):
    """A charm part is fully specified."""
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: somebase
            channel: "30.04"
        parts:
          charm:
            plugin: charm
    """
    )
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


def test_schema_doublelayer_parts_with_charm_plugin_different(create_config):
    """There is a 'charm' part but using a different plugin."""
    tmp_path = create_config(
        """
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
    )
    config = load(tmp_path)
    assert config.parts == {
        "charm": {
            "plugin": "dump",
            "source": "https://the.net/whatever.tar.gz",
            "source-type": "tar",
        }
    }


def test_schema_doublelayer_parts_with_charm_overriding_properties(create_config):
    """A charm plugin is used and its default properties are overridden."""
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: somebase
            channel: "30.04"
        parts:
          charm:
            charm-entrypoint: different.py
    """
    )
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


def test_schema_doublelayer_parts_with_charm_validating_props(create_config, check_schema_error):
    """A charm plugin is used and its validation schema is triggered ok."""
    create_config(
        """
        type: charm
        bases:
          - name: somebase
            channel: "30.04"
        parts:
          charm:
            charm-point: different.py  # misspelled!
    """
    )
    check_schema_error(
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


def test_charmhub_underscore_in_names(create_config, check_schema_error):
    """Do not support underscore in attributes, only dash."""
    create_config(
        """
        type: bundle  # mandatory
        charmhub:
            storage_url: https://server1.com
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - extra field 'storage_url' not permitted in 'charmhub' configuration"""
    )


# -- tests for bases


def test_no_bases_is_ok_for_bundles(emitter, create_config, tmp_path):
    """Do not send a deprecation message if it is a bundle."""
    create_config(
        """
        type: bundle
    """
    )

    load(tmp_path)
    assert not emitter.interactions


def test_bases_forbidden_for_bundles(create_config, check_schema_error):
    """Do not allow a bases configuration for bundles."""
    create_config(
        """
        type: bundle
        bases:
          - build-on:
              - name: test-build-name
                channel: test-build-channel
    """
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - Field not allowed when type=bundle in field 'bases'"""
    )


def test_bases_minimal_long_form(create_config):
    tmp_path = create_config(
        """
        type: charm
        bases:
          - build-on:
              - name: test-build-name
                channel: test-build-channel
            run-on:
              - name: test-run-name
                channel: test-run-channel
    """
    )

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


def test_bases_extra_field_error(create_config, check_schema_error):
    create_config(
        """
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
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - extra field 'extra-extra' not permitted in 'bases[0].build-on[0]' configuration"""
    )


def test_bases_underscores_error(create_config, check_schema_error):
    create_config(
        """
        type: charm
        bases:
          - build_on:
              - name: test-name
                channel: test-build-channel
            run_on:
              - name: test-name
                channel: test-run-channel
    """
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - field 'build-on' required in 'bases[0]' configuration
        - field 'run-on' required in 'bases[0]' configuration
        - extra field 'build_on' not permitted in 'bases[0]' configuration
        - extra field 'run_on' not permitted in 'bases[0]' configuration"""
    )


def test_channel_is_yaml_number(create_config, check_schema_error):
    create_config(
        """
        type: charm
        bases:
          - build-on:
              - name: test-build-name
                channel: 20.10
            run-on:
              - name: test-run-name
                channel: test-run-channel
    """
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - string type expected in field 'bases[0].build-on[0].channel'"""
    )


def test_minimal_long_form_bases(create_config):
    tmp_path = create_config(
        """
        type: charm
        bases:
          - build-on:
              - name: test-build-name
                channel: test-build-channel
            run-on:
              - name: test-run-name
                channel: test-run-channel
    """
    )

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


def test_complex_long_form_bases(create_config):
    tmp_path = create_config(
        """
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
    )

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


def test_multiple_long_form_bases(create_config):
    tmp_path = create_config(
        """
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
    )

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


def test_bases_minimal_short_form(create_config):
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: test-name
            channel: test-channel
    """
    )

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


def test_bases_short_form_extra_field_error(create_config, check_schema_error):
    create_config(
        """
        type: charm
        bases:
          - name: test-name
            channel: test-channel
            extra-extra: read all about it
    """
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - extra field 'extra-extra' not permitted in 'bases[0]' configuration"""
    )


def test_bases_short_form_missing_field_error(create_config, check_schema_error):
    create_config(
        """
        type: charm
        bases:
          - name: test-name
    """
    )

    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - field 'channel' required in 'bases[0]' configuration"""
    )


def test_bases_mixed_form_errors(create_config, check_schema_error):
    """Only the short-form errors are exposed as its the first validation pass."""
    create_config(
        """
        type: charm
        bases:
          - name: test-name
          - build-on:
              - name: test-build-name
            run-on:
              - name: test-run-name
    """
    )

    check_schema_error(
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


def test_schema_analysis_missing(create_config, tmp_path):
    """No analysis configuration leads to some defaults in place."""
    create_config(
        """
        type: bundle  # mandatory
    """
    )
    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == []


def test_schema_analysis_full_struct_just_empty(create_config, tmp_path):
    """Complete analysis structure, empty."""
    create_config(
        """
        type: bundle  # mandatory
        analysis:
            ignore:
                attributes: []
                linters: []
    """
    )
    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == []


def test_schema_analysis_ignore_attributes(create_config, tmp_path, create_checker):
    """Some attributes are correctly ignored."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.attribute)
    create_config(
        """
        type: bundle  # mandatory
        analysis:
            ignore:
                attributes: [check_ok_1, check_ok_2]
    """
    )
    config = load(tmp_path)
    assert config.analysis.ignore.attributes == ["check_ok_1", "check_ok_2"]
    assert config.analysis.ignore.linters == []


def test_schema_analysis_ignore_linters(create_config, tmp_path, create_checker):
    """Some linters are correctly ignored."""
    create_checker("check_ok_1", linters.CheckType.lint)
    create_checker("check_ok_2", linters.CheckType.lint)
    create_config(
        """
        type: bundle  # mandatory
        analysis:
            ignore:
                linters: [check_ok_1, check_ok_2]
    """
    )
    config = load(tmp_path)
    assert config.analysis.ignore.attributes == []
    assert config.analysis.ignore.linters == ["check_ok_1", "check_ok_2"]


def test_schema_analysis_ignore_attribute_missing(
    create_config, check_schema_error, tmp_path, create_checker
):
    """An attribute specified to ignore is missing in the system."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.lint)
    create_config(
        """
        type: bundle  # mandatory
        analysis:
            ignore:
                attributes: [check_ok_1, check_missing]
                linters: [check_ok_2]
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - Bad attribute name 'check_missing' in field 'analysis.ignore.attributes[1]'"""
    )


def test_schema_analysis_ignore_linter_missing(
    create_config, check_schema_error, tmp_path, create_checker
):
    """A linter specified to ignore is missing in the system."""
    create_checker("check_ok_1", linters.CheckType.attribute)
    create_checker("check_ok_2", linters.CheckType.lint)
    create_config(
        """
        type: bundle  # mandatory
        analysis:
            ignore:
                attributes: [check_ok_1]
                linters: [check_ok_2, check_missing]
    """
    )
    check_schema_error(
        """\
        Bad charmcraft.yaml content:
        - Bad lint name 'check_missing' in field 'analysis.ignore.linters[1]'"""
    )
