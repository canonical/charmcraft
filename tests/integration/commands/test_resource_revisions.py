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
"""Tests for resource-revisions command."""
import datetime
from argparse import Namespace
from unittest import mock

import pydantic
import pytest
from craft_store.models.resource_revision_model import (
    CharmResourceRevision,
    ResponseCharmResourceBase,
)

from charmcraft import store
from charmcraft.application.commands import ListResourceRevisionsCommand
from charmcraft.cmdbase import JSON_FORMAT
from charmcraft.env import CharmhubConfig


@pytest.fixture
def store_mock():
    """The fixture to fake the store layer in all the tests."""
    store_mock = mock.Mock(spec_set=store.Store)

    def validate_params(config, ephemeral=False, needs_auth=True):
        """Check that the store received the Charmhub configuration and ephemeral flag."""
        assert config == CharmhubConfig()
        assert isinstance(ephemeral, bool)
        assert isinstance(needs_auth, bool)
        return store_mock

    with mock.patch("charmcraft.application.commands.store.Store", validate_params):
        yield store_mock


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resourcerevisions_simple(emitter, store_mock, config, formatted):
    """Happy path of one result from the Store."""
    store_response = [
        CharmResourceRevision(
            revision=1,
            size=pydantic.ByteSize(50),
            created_at=datetime.datetime(2020, 7, 3, 2, 30, 40, tzinfo=datetime.timezone.utc),
            bases=[ResponseCharmResourceBase()],
            name="testresource",
            sha256="",
            sha3_384="",
            sha384="",
            sha512="",
            type="file",
        ),
    ]
    store_mock.list_resource_revisions.return_value = store_response

    args = Namespace(charm_name="testcharm", resource_name="testresource", format=formatted)
    ListResourceRevisionsCommand(config).run(args)

    assert store_mock.mock_calls == [
        mock.call.list_resource_revisions("testcharm", "testresource"),
    ]
    if formatted:
        expected = [
            {
                "revision": 1,
                "created at": "2020-07-03T02:30:40+00:00",
                "size": 50,
                "bases": [{"name": "all", "channel": "all", "architectures": ["all"]}],
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Created at              Size  Architectures",
            "1           2020-07-03T02:30:40Z     50B  all",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resourcerevisions_empty(emitter, store_mock, config, formatted):
    """No results from the store."""
    store_response = []
    store_mock.list_resource_revisions.return_value = store_response

    args = Namespace(charm_name="testcharm", resource_name="testresource", format=formatted)
    ListResourceRevisionsCommand(config).run(args)

    if formatted:
        emitter.assert_json_output([])
    else:
        emitter.assert_message("No revisions found.")


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resourcerevisions_ordered_by_revision(emitter, store_mock, config, formatted):
    """Results are presented ordered by revision in the table."""
    # three Revisions with all values weirdly similar, the only difference is revision, so
    # we really assert later that it was used for ordering
    tstamp = datetime.datetime(2020, 7, 3, 20, 30, 40, tzinfo=datetime.timezone.utc)
    store_response = [
        CharmResourceRevision(
            revision=1,
            size=pydantic.ByteSize(5000),
            created_at=tstamp,
            bases=[],
            name="testresource",
            sha256="",
            sha3_384="",
            sha384="",
            sha512="",
            type="file",
        ),
        CharmResourceRevision(
            revision=3,
            size=pydantic.ByteSize(34450520),
            created_at=tstamp,
            bases=[],
            name="testresource",
            sha256="",
            sha3_384="",
            sha384="",
            sha512="",
            type="file",
        ),
        CharmResourceRevision(
            revision=4,
            size=pydantic.ByteSize(876543),
            created_at=tstamp,
            bases=[ResponseCharmResourceBase(architectures=["amd64", "arm64"])],
            name="testresource",
            sha256="",
            sha3_384="",
            sha384="",
            sha512="",
            type="file",
        ),
        CharmResourceRevision(
            revision=2,
            size=pydantic.ByteSize(50),
            created_at=tstamp,
            bases=[],
            name="testresource",
            sha256="",
            sha3_384="",
            sha384="",
            sha512="",
            type="file",
        ),
    ]
    store_mock.list_resource_revisions.return_value = store_response

    args = Namespace(charm_name="testcharm", resource_name="testresource", format=formatted)
    ListResourceRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 1,
                "created at": "2020-07-03T20:30:40+00:00",
                "size": 5000,
                "bases": [],
            },
            {
                "revision": 3,
                "created at": "2020-07-03T20:30:40+00:00",
                "size": 34450520,
                "bases": [],
            },
            {
                "revision": 4,
                "created at": "2020-07-03T20:30:40+00:00",
                "size": 876543,
                "bases": [{"name": "all", "channel": "all", "architectures": ["amd64", "arm64"]}],
            },
            {"revision": 2, "created at": "2020-07-03T20:30:40+00:00", "size": 50, "bases": []},
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Created at              Size  Architectures",
            "4           2020-07-03T20:30:40Z  856.0K  amd64,arm64",
            "3           2020-07-03T20:30:40Z   32.9M",
            "2           2020-07-03T20:30:40Z     50B",
            "1           2020-07-03T20:30:40Z    4.9K",
        ]
        emitter.assert_messages(expected)
