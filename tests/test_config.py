# Copyright 2020-2021 Canonical Ltd.
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
from textwrap import dedent
from unittest.mock import patch

import pytest

from charmcraft.cmdbase import CommandError
from charmcraft.config import (
    CharmhubConfig,
    Part,
    check_relative_paths,
    load,
)


@pytest.fixture
def create_config(tmp_path):
    """Helper to create the config."""

    def create_config(text):
        test_file = tmp_path / "charmcraft.yaml"
        test_file.write_text(text)
        return tmp_path

    return create_config


# -- tests for the config loading


def test_load_current_directory(create_config, monkeypatch):
    """Init the config using charmcraft.yaml in current directory."""
    tmp_path = create_config(
        """
        type: charm
    """
    )
    monkeypatch.chdir(tmp_path)
    fake_utcnow = datetime.datetime(1970, 1, 1, 0, 0, 2, tzinfo=datetime.timezone.utc)
    with patch("datetime.datetime") as mock:
        mock.utcnow.return_value = fake_utcnow
        config = load(None)
    assert config.type == "charm"
    assert config.project.dirpath == tmp_path
    assert config.project.config_provided
    assert config.project.started_at == fake_utcnow


def test_load_specific_directory_ok(create_config):
    """Init the config using charmcraft.yaml in a specific directory."""
    tmp_path = create_config(
        """
        type: charm
    """
    )
    config = load(tmp_path)
    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


def test_load_optional_charmcraft_missing(tmp_path):
    """Specify a directory where the file is missing."""
    config = load(tmp_path)
    assert config.type == "undefined"
    assert config.project.dirpath == tmp_path
    assert not config.project.config_provided


def test_load_specific_directory_resolved(create_config, monkeypatch):
    """Ensure that the given directory is resolved to always show the whole path."""
    tmp_path = create_config(
        """
        type: charm
    """
    )
    # change to some dir, and reference the config dir relatively
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    config = load("../")

    assert config.type == "charm"
    assert config.project.dirpath == tmp_path


def test_load_specific_directory_expanded(create_config, monkeypatch):
    """Ensure that the given directory is user-expanded."""
    tmp_path = create_config(
        """
        type: charm
    """
    )
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
        """The real checker.

        Note this compares for multiple messages, as for Python 3.5 we don't have control on
        which of the verifications it will fail. After 3.5 is dropped this could be changed
        to receive only one message and compare with equality below, not inclusion.
        """
        with pytest.raises(CommandError) as cm:
            load(tmp_path)
        assert str(cm.value) == expected_msg

    return check_schema_error


def test_schema_top_level_no_extra_properties(create_config, check_schema_error):
    """Schema validation, can not add undefined properties at the top level."""
    create_config(
        """
        type: bundle
        whatever: new-stuff
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: whatever
              reason: extra fields not permitted"""
        )
    )


def test_schema_type_missing(create_config, check_schema_error):
    """Schema validation, type is mandatory."""
    create_config(
        """
        charmhub:
            api_url: https://www.canonical.com
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: type
              reason: field required"""
        )
    )


def test_schema_type_bad_type(create_config, check_schema_error):
    """Schema validation, type is a string."""
    create_config(
        """
        type: 33
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: type
              reason: string type expected"""
        )
    )


def test_schema_type_limited_values(create_config, check_schema_error):
    """Schema validation, type must be a subset of values."""
    create_config(
        """
        type: whatever
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: type
              reason: must be either 'charm' or 'bundle'"""
        )
    )


def test_schema_charmhub_api_url_bad_type(create_config, check_schema_error):
    """Schema validation, charmhub.api_url must be a string."""
    create_config(
        """
        type: charm  # mandatory
        charmhub:
            api_url: 33
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: charmhub.api_url
              reason: invalid or missing URL scheme"""
        )
    )


def test_schema_charmhub_api_url_bad_format(create_config, check_schema_error):
    """Schema validation, charmhub.api_url must be a full URL."""
    create_config(
        """
        type: charm  # mandatory
        charmhub:
            api_url: stuff.com
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: charmhub.api_url
              reason: invalid or missing URL scheme"""
        )
    )


def test_schema_charmhub_storage_url_bad_type(create_config, check_schema_error):
    """Schema validation, charmhub.storage_url must be a string."""
    create_config(
        """
        type: charm  # mandatory
        charmhub:
            storage_url: 33
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: charmhub.storage_url
              reason: invalid or missing URL scheme"""
        )
    )


def test_schema_charmhub_storage_url_bad_format(create_config, check_schema_error):
    """Schema validation, charmhub.storage_url must be a full URL."""
    create_config(
        """
        type: charm  # mandatory
        charmhub:
            storage_url: stuff.com
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: charmhub.storage_url
              reason: invalid or missing URL scheme"""
        )
    )


def test_schema_charmhub_no_extra_properties(create_config, check_schema_error):
    """Schema validation, can not add undefined properties in charmhub key."""
    create_config(
        """
        type: bundle
        charmhub:
            storage_url: https://some.server.com
            crazy: false
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: charmhub.crazy
              reason: extra fields not permitted"""
        )
    )


def test_schema_basicprime_bad_init_structure(create_config, check_schema_error):
    """Schema validation, basic prime with bad parts."""
    create_config(
        """
        type: charm  # mandatory
        parts: ['foo', 'bar']
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: parts
              reason: value is not a valid dict"""
        )
    )


def test_schema_basicprime_bad_bundle_structure(create_config, check_schema_error):
    """Instantiate charmhub using a bad structure."""
    """Schema validation, basic prime with bad bundle."""
    create_config(
        """
        type: charm  # mandatory
        parts:
            bundle: ['foo', 'bar']
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: parts.bundle
              reason: value is not a valid dict"""
        )
    )


def test_schema_basicprime_bad_prime_structure(create_config, check_schema_error):
    """Schema validation, basic prime with bad prime."""
    create_config(
        """
        type: charm  # mandatory
        parts:
            bundle:
                prime: foo
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: parts.bundle.prime
              reason: value is not a valid list"""
        )
    )


def test_schema_basicprime_bad_content_type(create_config, check_schema_error):
    """Schema validation, basic prime with a prime holding not strings."""
    create_config(
        """
        type: charm  # mandatory
        parts:
            bundle:
                prime: [33, 'foo']
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: parts.bundle.prime[0]
              reason: string type expected"""
        )
    )


def test_schema_basicprime_bad_content_format(create_config, check_schema_error):
    """Schema validation, basic prime with a prime holding not strings."""
    create_config(
        """
        type: charm  # mandatory
        parts:
            bundle:
                prime: ['/bar/foo', 'foo']
    """
    )
    check_schema_error(
        dedent(
            """\
            Bad charmcraft.yaml content:
            - field: parts.bundle.prime[0]
              reason: must be a valid relative path"""
        )
    )


# -- tests for different validators


def test_relativepaths_ok():
    """Indicated paths must be relative."""
    assert check_relative_paths("foo/bar")


def test_relativepaths_absolute():
    """Indicated paths must be relative."""
    with pytest.raises(ValueError) as cm:
        check_relative_paths("/foo/bar")
    assert str(cm.value) == "must be a valid relative path"


def test_relativepaths_empty():
    """Indicated paths must be relative."""
    with pytest.raises(ValueError) as cm:
        check_relative_paths("")
    assert str(cm.value) == "must be a valid relative path"


def test_relativepaths_nonstring():
    """Indicated paths must be relative."""
    with pytest.raises(ValueError) as cm:
        check_relative_paths(33)
    assert str(cm.value) == "must be a valid relative path"


# -- tests for Charmhub config


def test_charmhub_frozen():
    """Cannot change values from the charmhub config."""
    config = CharmhubConfig()
    with pytest.raises(TypeError):
        config.api_url = "broken"


# -- tests for BasicPrime config


def test_basicprime_frozen():
    """Cannot change values from the charmhub config."""
    config = Part(prime=["foo", "bar"])
    with pytest.raises(TypeError):
        config[0] = "broken"


def test_basicprime_ok():
    """A simple building ok."""
    config = Part(prime=["foo", "bar"])
    with pytest.raises(TypeError):
        config.prime = "broken"
    assert config.prime == ["foo", "bar"]


def test_basicprime_empty():
    """Building with an empty list."""
    config = Part(prime=[])
    assert config.prime == []
