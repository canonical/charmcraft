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

"""Tests for the Store commands (code in store/__init__.py)."""

import base64
import datetime
import sys
import zipfile
from argparse import ArgumentParser, Namespace
from unittest.mock import ANY, MagicMock, Mock, call, patch

import dateutil.parser
import pydantic
import pytest
import yaml
from craft_cli import CraftError
from craft_store.errors import CredentialsUnavailable, StoreServerError

from charmcraft.cmdbase import JSON_FORMAT
from charmcraft.commands.store import (
    CloseCommand,
    CreateLibCommand,
    EntityType,
    FetchLibCommand,
    ListLibCommand,
    ListNamesCommand,
    ListResourceRevisionsCommand,
    ListResourcesCommand,
    ListRevisionsCommand,
    LoginCommand,
    LogoutCommand,
    PublishLibCommand,
    RegisterBundleNameCommand,
    RegisterCharmNameCommand,
    ReleaseCommand,
    StatusCommand,
    UnregisterNameCommand,
    UploadCommand,
    UploadResourceCommand,
    WhoamiCommand,
    get_name_from_zip,
)
from charmcraft.commands.store.store import (
    Account,
    Base,
    Channel,
    Entity,
    Error,
    Library,
    MacaroonInfo,
    Package,
    RegistryCredentials,
    Release,
    Resource,
    ResourceRevision,
    Revision,
    Uploaded,
)
from charmcraft.main import ArgumentParsingError
from charmcraft.models.charmcraft import CharmhubConfig
from charmcraft.utils import (
    ResourceOption,
    SingleOptionEnsurer,
    get_templates_environment,
    useful_filepath,
)
from tests import factory

# used a lot!
noargs = Namespace()

# used to flag defaults when None is a real option
DEFAULT = object()


def _fake_response(status_code, reason=None, json=None):
    response = Mock(spec="requests.Response")
    response.status_code = status_code
    response.ok = status_code == 200
    response.reason = reason
    if json is not None:
        response.json = Mock(return_value=json)
    return response


@pytest.fixture()
def store_mock():
    """The fixture to fake the store layer in all the tests."""
    store_mock = MagicMock()

    def validate_params(config, ephemeral=False, needs_auth=True):
        """Check that the store received the Charmhub configuration and ephemeral flag."""
        assert config == CharmhubConfig()
        assert isinstance(ephemeral, bool)
        assert isinstance(needs_auth, bool)
        return store_mock

    with patch("charmcraft.commands.store.Store", validate_params):
        yield store_mock


@pytest.fixture()
def add_cleanup():
    """Generic cleaning helper."""
    to_cleanup = []

    def f(func, *args, **kwargs):
        """Store the cleaning actions for later."""
        to_cleanup.append((func, args, kwargs))

    yield f

    for func, args, kwargs in to_cleanup:
        func(*args, **kwargs)


# -- tests for auth commands

LOGIN_OPTIONS = dict.fromkeys(["export", "charm", "bundle", "permission", "channel", "ttl"])


def test_login_simple(emitter, store_mock, config):
    """Simple login case."""
    store_mock.whoami.return_value = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=None,
        packages=None,
    )

    args = Namespace(**LOGIN_OPTIONS)
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(),
        call.whoami(),
    ]
    emitter.assert_message("Logged in as 'jdoe'.")


def test_login_exporting(emitter, store_mock, config, tmp_path):
    """Login with exported credentials."""
    acquired_credentials = "super secret stuff"
    store_mock.login.return_value = acquired_credentials

    credentials_file = tmp_path / "somefile.txt"
    args = Namespace(**LOGIN_OPTIONS)
    args.export = credentials_file
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(),
    ]
    emitter.assert_message(f"Login successful. Credentials exported to {str(credentials_file)!r}.")
    assert credentials_file.read_text() == acquired_credentials


@pytest.mark.parametrize("rest_option", ["charm", "bundle", "permission", "channel", "ttl"])
def test_login_restrictions_without_export(emitter, store_mock, config, tmp_path, rest_option):
    """Login restrictions are not allowed if export option is not used."""
    args = Namespace(**LOGIN_OPTIONS)
    setattr(args, rest_option, "used")
    with pytest.raises(ArgumentParsingError) as cm:
        LoginCommand(config).run(args)
    assert str(cm.value) == (
        "The restrictive options 'bundle', 'channel', 'charm', 'permission' or 'ttl' "
        "can only be used when credentials are exported."
    )


def test_login_restricting_ttl(emitter, store_mock, config, tmp_path):
    """Login with a TTL restriction."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.ttl = 1000
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(ttl=1000),
    ]


def test_login_restricting_channels(emitter, store_mock, config, tmp_path):
    """Login with channels restriction."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.channel = ["edge", "beta"]
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(channels=["edge", "beta"]),
    ]


def test_login_restricting_permissions(emitter, store_mock, config, tmp_path):
    """Login with permissions restriction."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.permission = ["package-view-metadata", "package-manage-metadata"]
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(permissions=["package-view-metadata", "package-manage-metadata"]),
    ]


def test_login_restricting_permission_invalid(emitter, store_mock, config, tmp_path):
    """Login with a permission restriction that is not valid."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.permission = ["absolute-power", "package-manage-metadata", "crazy-stuff"]
    with pytest.raises(CraftError) as cm:
        LoginCommand(config).run(args)

    assert str(cm.value) == "Invalid permission: 'absolute-power', 'crazy-stuff'."
    assert cm.value.details == (
        "Explore the documentation to learn about valid permissions: "
        "https://juju.is/docs/sdk/remote-env-auth"
    )


def test_login_restricting_charms(emitter, store_mock, config, tmp_path):
    """Login with charms restriction."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.charm = ["charm1", "charm2"]
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(charms=["charm1", "charm2"]),
    ]


def test_login_restricting_bundles(emitter, store_mock, config, tmp_path):
    """Login with bundles restriction."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(**LOGIN_OPTIONS)
    args.export = tmp_path / "somefile.txt"
    args.bundle = ["bundle1", "bundle2"]
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(bundles=["bundle1", "bundle2"]),
    ]


def test_login_restriction_mix(emitter, store_mock, config, tmp_path):
    """Valid case combining several restrictions."""
    store_mock.login.return_value = "super secret stuff"

    args = Namespace(
        export=tmp_path / "somefile.txt",
        charm=["mycharm"],
        bundle=None,
        permission=["package-view", "package-manage"],
        channel=["edge"],
        ttl=259200,
    )
    LoginCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.login(
            ttl=259200,
            channels=["edge"],
            charms=["mycharm"],
            permissions=["package-view", "package-manage"],
        ),
    ]


def test_logout(emitter, store_mock, config):
    """Simple logout case."""
    LogoutCommand(config).run(noargs)

    assert store_mock.mock_calls == [
        call.logout(),
    ]
    emitter.assert_message("Charmhub token cleared.")


def test_logout_but_not_logged_in(emitter, store_mock, config):
    """Simple logout case."""
    store_mock.logout.side_effect = CredentialsUnavailable(
        application="charmcraft", host="api.charmcraft.io"
    )

    LogoutCommand(config).run(noargs)

    assert store_mock.mock_calls == [
        call.logout(),
    ]
    emitter.assert_message("You are not logged in to Charmhub.")


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_whoami(emitter, store_mock, config, formatted):
    """Simple whoami case."""
    store_response = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=None,
        packages=None,
    )
    store_mock.whoami.return_value = store_response

    args = Namespace(format=formatted)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    if formatted:
        expected = {
            "logged": True,
            "name": "John Doe",
            "username": "jdoe",
            "id": "dlq8hl8hd8qhdl3lhl",
            "permissions": ["perm1", "perm2"],
        }
        emitter.assert_json_output(expected)
    else:
        expected = [
            "name: John Doe",
            "username: jdoe",
            "id: dlq8hl8hd8qhdl3lhl",
            "permissions:",
            "- perm1",
            "- perm2",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_whoami_but_not_logged_in(emitter, store_mock, config, formatted):
    """Whoami when not logged."""
    store_mock.whoami.side_effect = CredentialsUnavailable(
        application="charmcraft", host="api.charmcraft.io"
    )

    args = Namespace(format=formatted)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    if formatted:
        expected = {
            "logged": False,
        }
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message("You are not logged in to Charmhub.")


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_whoami_with_channels(emitter, store_mock, config, formatted):
    """Whoami with channel attenuations."""
    store_response = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=["edge", "beta"],
        packages=None,
    )
    store_mock.whoami.return_value = store_response

    args = Namespace(format=formatted)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    if formatted:
        expected = {
            "logged": True,
            "name": "John Doe",
            "username": "jdoe",
            "id": "dlq8hl8hd8qhdl3lhl",
            "permissions": ["perm1", "perm2"],
            "channels": ["edge", "beta"],
        }
        emitter.assert_json_output(expected)
    else:
        expected = [
            "name: John Doe",
            "username: jdoe",
            "id: dlq8hl8hd8qhdl3lhl",
            "permissions:",
            "- perm1",
            "- perm2",
            "channels:",
            "- edge",
            "- beta",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_whoami_with_charms(emitter, store_mock, config, formatted):
    """Whoami with charms attenuations."""
    store_response = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=None,
        packages=[
            Package(type="charm", name="charmname1", id=None),
            Package(type="charm", name=None, id="charmid2"),
        ],
    )
    store_mock.whoami.return_value = store_response

    args = Namespace(format=formatted)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    if formatted:
        expected = {
            "logged": True,
            "name": "John Doe",
            "username": "jdoe",
            "id": "dlq8hl8hd8qhdl3lhl",
            "permissions": ["perm1", "perm2"],
            "charms": [{"name": "charmname1"}, {"id": "charmid2"}],
        }
        emitter.assert_json_output(expected)
    else:
        expected = [
            "name: John Doe",
            "username: jdoe",
            "id: dlq8hl8hd8qhdl3lhl",
            "permissions:",
            "- perm1",
            "- perm2",
            "charms:",
            "- name: charmname1",
            "- id: charmid2",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_whoami_with_bundles(emitter, store_mock, config, formatted):
    """Whoami with bundles attenuations."""
    store_response = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=None,
        packages=[
            Package(type="bundle", name="bundlename1", id=None),
            Package(type="bundle", name=None, id="bundleid2"),
        ],
    )
    store_mock.whoami.return_value = store_response

    args = Namespace(format=formatted)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    if formatted:
        expected = {
            "logged": True,
            "name": "John Doe",
            "username": "jdoe",
            "id": "dlq8hl8hd8qhdl3lhl",
            "permissions": ["perm1", "perm2"],
            "bundles": [{"name": "bundlename1"}, {"id": "bundleid2"}],
        }
        emitter.assert_json_output(expected)
    else:
        expected = [
            "name: John Doe",
            "username: jdoe",
            "id: dlq8hl8hd8qhdl3lhl",
            "permissions:",
            "- perm1",
            "- perm2",
            "bundles:",
            "- name: bundlename1",
            "- id: bundleid2",
        ]
        emitter.assert_messages(expected)


def test_whoami_comprehensive(emitter, store_mock, config):
    """Whoami with ALL attenuations."""
    store_response = MacaroonInfo(
        account=Account(name="John Doe", username="jdoe", id="dlq8hl8hd8qhdl3lhl"),
        permissions=["perm1", "perm2"],
        channels=["edge", "beta"],
        packages=[
            Package(type="charm", name="charmname1", id=None),
            Package(type="charm", name=None, id="charmid2"),
            Package(type="bundle", name="bundlename", id=None),
        ],
    )
    store_mock.whoami.return_value = store_response

    args = Namespace(format=False)
    WhoamiCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.whoami(),
    ]
    expected = [
        "name: John Doe",
        "username: jdoe",
        "id: dlq8hl8hd8qhdl3lhl",
        "permissions:",
        "- perm1",
        "- perm2",
        "charms:",
        "- name: charmname1",
        "- id: charmid2",
        "bundles:",
        "- name: bundlename",
        "channels:",
        "- edge",
        "- beta",
    ]
    emitter.assert_messages(expected)


# -- tests for name-related commands


def test_register_charm_name(emitter, store_mock, config):
    """Simple register_name case for a charm."""
    args = Namespace(name="testname")
    RegisterCharmNameCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.register_name("testname", EntityType.charm),
    ]
    expected = "You are now the publisher of charm 'testname' in Charmhub."
    emitter.assert_message(expected)


def test_register_bundle_name(emitter, store_mock, config):
    """Simple register_name case for a bundl."""
    args = Namespace(name="testname")
    RegisterBundleNameCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.register_name("testname", EntityType.bundle),
    ]
    expected = "You are now the publisher of bundle 'testname' in Charmhub."
    emitter.assert_message(expected)


def test_unregister_name(emitter, store_mock, config):
    """Simple name unregsitration name."""
    args = Namespace(name="testname")
    UnregisterNameCommand(config).run(args)

    assert store_mock.mock_calls == [call.unregister_name("testname")]
    emitter.assert_message("Name 'testname' has been removed from Charmhub.")


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_list_registered_empty(emitter, store_mock, config, formatted):
    """List registered with empty response."""
    store_response = []
    store_mock.list_registered_names.return_value = store_response

    args = Namespace(format=formatted, include_collaborations=None)
    ListNamesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_registered_names(include_collaborations=None),
    ]
    if formatted:
        emitter.assert_json_output([])
    else:
        expected = "No charms or bundles registered."
        emitter.assert_message(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_list_registered_one_private(emitter, store_mock, config, formatted):
    """List registered with one private item in the response."""
    store_response = [
        Entity(
            entity_type="charm",
            name="charm",
            private=True,
            status="status",
            publisher_display_name="J. Doe",
        ),
    ]
    store_mock.list_registered_names.return_value = store_response

    args = Namespace(format=formatted, include_collaborations=None)
    ListNamesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_registered_names(include_collaborations=None),
    ]
    expected = [
        "Name    Type    Visibility    Status",
        "charm   charm   private       status",
    ]
    if formatted:
        expected = [
            {
                "name": "charm",
                "type": "charm",
                "visibility": "private",
                "status": "status",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_list_registered_one_public(emitter, store_mock, config, formatted):
    """List registered with one public item in the response."""
    store_response = [
        Entity(
            entity_type="charm",
            name="charm",
            private=False,
            status="status",
            publisher_display_name="J. Doe",
        ),
    ]
    store_mock.list_registered_names.return_value = store_response

    args = Namespace(format=formatted, include_collaborations=None)
    ListNamesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_registered_names(include_collaborations=None),
    ]
    expected = [
        "Name    Type    Visibility    Status",
        "charm   charm   public        status",
    ]
    if formatted:
        expected = [
            {
                "name": "charm",
                "type": "charm",
                "visibility": "public",
                "status": "status",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_list_registered_several(emitter, store_mock, config, formatted):
    """List registered with several itemsssssssss in the response."""
    store_response = [
        Entity(
            entity_type="charm",
            name="charm1",
            private=True,
            status="simple status",
            publisher_display_name="J. Doe",
        ),
        Entity(
            entity_type="charm",
            name="charm2-long-name",
            private=False,
            status="other",
            publisher_display_name="J. Doe",
        ),
        Entity(
            entity_type="charm",
            name="charm3",
            private=True,
            status="super long status",
            publisher_display_name="J. Doe",
        ),
        Entity(
            entity_type="bundle",
            name="somebundle",
            private=False,
            status="bundle status",
            publisher_display_name="J. Doe",
        ),
    ]
    store_mock.list_registered_names.return_value = store_response

    args = Namespace(format=formatted, include_collaborations=None)
    ListNamesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_registered_names(include_collaborations=None),
    ]
    if formatted:
        expected = [
            {
                "name": "charm1",
                "type": "charm",
                "visibility": "private",
                "status": "simple status",
            },
            {
                "name": "charm2-long-name",
                "type": "charm",
                "visibility": "public",
                "status": "other",
            },
            {
                "name": "charm3",
                "type": "charm",
                "visibility": "private",
                "status": "super long status",
            },
            {
                "name": "somebundle",
                "type": "bundle",
                "visibility": "public",
                "status": "bundle status",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Name              Type    Visibility    Status",
            "charm1            charm   private       simple status",
            "charm2-long-name  charm   public        other",
            "charm3            charm   private       super long status",
            "somebundle        bundle  public        bundle status",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_list_registered_with_collaborations(emitter, store_mock, config, formatted):
    """List registered with collaborations flag."""
    store_response = [
        Entity(
            entity_type="charm",
            name="charm1",
            private=True,
            status="simple status",
            publisher_display_name="J. Doe",
        ),
        Entity(
            entity_type="bundle",
            name="somebundle",
            private=False,
            status="bundle status",
            publisher_display_name="Ms. Bundle Publisher",
        ),
    ]
    store_mock.list_registered_names.return_value = store_response

    args = Namespace(format=formatted, include_collaborations=True)
    ListNamesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_registered_names(include_collaborations=True),
    ]
    if formatted:
        expected = [
            {
                "name": "charm1",
                "type": "charm",
                "visibility": "private",
                "status": "simple status",
                "publisher": "J. Doe",
            },
            {
                "name": "somebundle",
                "type": "bundle",
                "visibility": "public",
                "status": "bundle status",
                "publisher": "Ms. Bundle Publisher",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Name        Type    Visibility    Status         Publisher",
            "charm1      charm   private       simple status  J. Doe",
            "somebundle  bundle  public        bundle status  Ms. Bundle Publisher",
        ]
        emitter.assert_messages(expected)


# -- tests for upload command


def _build_zip_with_yaml(zippath, filename, *, content=None, raw_yaml=None):
    """Create a yaml named 'filename' with given content, inside a zip file in 'zippath'."""
    if raw_yaml is None:
        raw_yaml = yaml.dump(content).encode("ascii")
    with zipfile.ZipFile(str(zippath), "w") as zf:
        zf.writestr(filename, raw_yaml)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_get_name_bad_zip(tmp_path):
    """Get the name from a bad zip file."""
    bad_zip = tmp_path / "badstuff.zip"
    bad_zip.write_text("I'm not really a zip file")

    with pytest.raises(CraftError) as cm:
        get_name_from_zip(bad_zip)
    assert str(cm.value) == f"Cannot open '{bad_zip}' (bad zip file)."


def test_get_name_charm_ok(tmp_path):
    """Get the name from a charm file, all ok."""
    test_zip = tmp_path / "some.zip"
    test_name = "whatever"
    _build_zip_with_yaml(test_zip, "metadata.yaml", content={"name": test_name})

    name = get_name_from_zip(test_zip)
    assert name == test_name


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "yaml_content",
    [
        b"=",  # invalid yaml
        b"foo: bar",  # missing 'name'
    ],
)
def test_get_name_charm_bad_metadata(tmp_path, yaml_content):
    """Get the name from a charm file, but with a wrong metadata.yaml."""
    bad_zip = tmp_path / "badstuff.zip"
    _build_zip_with_yaml(bad_zip, "metadata.yaml", raw_yaml=yaml_content)

    with pytest.raises(CraftError) as cm:
        get_name_from_zip(bad_zip)
    assert str(cm.value) == (
        "Bad 'metadata.yaml' file inside charm zip "
        "'{}': must be a valid YAML with a 'name' key.".format(bad_zip)
    )
    assert cm.value.__cause__ is not None


def test_get_name_bundle_ok(tmp_path):
    """Get the name from a bundle file, all ok."""
    test_zip = tmp_path / "some.zip"
    test_name = "whatever"
    _build_zip_with_yaml(test_zip, "bundle.yaml", content={"name": test_name})

    name = get_name_from_zip(test_zip)
    assert name == test_name


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "yaml_content",
    [
        b"=",  # invalid yaml
        b"foo: bar",  # missing 'name'
    ],
)
def test_get_name_bundle_bad_data(tmp_path, yaml_content):
    """Get the name from a bundle file, but with a bad bundle.yaml."""
    bad_zip = tmp_path / "badstuff.zip"
    _build_zip_with_yaml(bad_zip, "bundle.yaml", raw_yaml=yaml_content)

    with pytest.raises(CraftError) as cm:
        get_name_from_zip(bad_zip)
    assert str(cm.value) == (
        "Bad 'bundle.yaml' file inside bundle zip '{}': "
        "must be a valid YAML with a 'name' key.".format(bad_zip)
    )
    assert cm.value.__cause__ is not None


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_get_name_nor_charm_nor_bundle(tmp_path):
    """Get the name from a zip that has no metadata.yaml nor bundle.yaml."""
    bad_zip = tmp_path / "bad-stuff.zip"
    _build_zip_with_yaml(bad_zip, "whatever.yaml", content={})

    with pytest.raises(CraftError) as cm:
        get_name_from_zip(bad_zip)
    assert str(cm.value) == (
        "The indicated zip file '{}' is not a charm ('metadata.yaml' not found) nor a bundle "
        "('bundle.yaml' not found).".format(bad_zip)
    )


def test_upload_parameters_filepath_type(config):
    """The filepath parameter implies a set of validations."""
    cmd = UploadCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "filepath")
    assert action.type is useful_filepath


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_upload_call_ok(emitter, store_mock, config, tmp_path, formatted):
    """Simple upload, success result."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(filepath=test_charm, release=[], name=None, format=formatted)
    retcode = UploadCommand(config).run(args)
    assert retcode == 0

    assert store_mock.mock_calls == [call.upload("mycharm", test_charm)]
    if formatted:
        expected = {"revision": 7}
        emitter.assert_json_output(expected)
    else:
        expected = "Revision 7 of 'mycharm' created"
        emitter.assert_message(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_upload_call_error(emitter, store_mock, config, tmp_path, formatted):
    """Simple upload but with a response indicating an error."""
    errors = [
        Error(message="text 1", code="missing-stuff"),
        Error(message="other long error text", code="broken"),
    ]
    store_response = Uploaded(ok=False, status=400, revision=None, errors=errors)
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(filepath=test_charm, release=[], name=None, format=formatted)
    retcode = UploadCommand(config).run(args)
    assert retcode == 1

    assert store_mock.mock_calls == [call.upload("mycharm", test_charm)]
    if formatted:
        expected = {
            "errors": [
                {"code": "missing-stuff", "message": "text 1"},
                {"code": "broken", "message": "other long error text"},
            ]
        }
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Upload failed with status 400:",
            "- missing-stuff: text 1",
            "- broken: other long error text",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_upload_call_login_expired(mocker, monkeypatch, config, tmp_path, formatted):
    """Simple upload but login expired."""
    monkeypatch.setenv("CHARMCRAFT_AUTH", base64.b64encode(b"credentials").decode())
    mock_whoami = mocker.patch("craft_store.base_client.HTTPClient.request")
    push_file_mock = mocker.patch("charmcraft.commands.store.store.Client.push_file")

    mock_whoami.side_effect = StoreServerError(_fake_response(401, json={}))

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(filepath=test_charm, release=[], name=None, format=formatted)

    with pytest.raises(CraftError) as cm:
        UploadCommand(config).run(args)
    assert str(cm.value) == (
        "Provided credentials are no longer valid for Charmhub. Regenerate them and try again."
    )
    assert not push_file_mock.called


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_upload_call_ok_including_release(emitter, store_mock, config, tmp_path, formatted):
    """Upload with a release included, success result."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(
        filepath=test_charm, release=["edge"], resource=[], name=None, format=formatted
    )
    UploadCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.upload("mycharm", test_charm),
        call.release("mycharm", 7, ["edge"], []),
    ]
    if formatted:
        expected = {"revision": 7}
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision 7 of 'mycharm' created",
            "Revision released to edge",
        ]
        emitter.assert_messages(expected)


def test_upload_call_ok_including_release_multiple(emitter, store_mock, config, tmp_path):
    """Upload with release to two channels included, success result."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(
        filepath=test_charm, release=["edge", "stable"], resource=[], name=None, format=False
    )
    UploadCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.upload("mycharm", test_charm),
        call.release("mycharm", 7, ["edge", "stable"], []),
    ]
    expected = [
        "Revision 7 of 'mycharm' created",
        "Revision released to edge, stable",
    ]
    emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_upload_including_release_with_resources(emitter, store_mock, config, tmp_path, formatted):
    """Releasing with resources."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    r1 = ResourceOption(name="foo", revision=3)
    r2 = ResourceOption(name="bar", revision=17)
    args = Namespace(
        filepath=test_charm, release=["edge"], resource=[r1, r2], name=None, format=formatted
    )
    UploadCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.upload("mycharm", test_charm),
        call.release("mycharm", 7, ["edge"], [r1, r2]),
    ]
    if formatted:
        expected = {"revision": 7}
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision 7 of 'mycharm' created",
            "Revision released to edge (attaching resources: 'foo' r3, 'bar' r17)",
        ]
        emitter.assert_messages(expected)


def test_upload_options_resource(config):
    """The --resource option implies a set of validations."""
    cmd = UploadCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "resource")
    assert isinstance(action.type, ResourceOption)


def test_upload_call_error_including_release(emitter, store_mock, config, tmp_path):
    """Upload with a realsea but the upload went wrong, so no release."""
    errors = [Error(message="text", code="problem")]
    store_response = Uploaded(ok=False, status=400, revision=None, errors=errors)
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(filepath=test_charm, release=["edge"], name=None, format=False)
    UploadCommand(config).run(args)

    # check the upload was attempted, but not the release!
    assert store_mock.mock_calls == [call.upload("mycharm", test_charm)]


def test_upload_with_different_name_than_in_metadata(emitter, store_mock, config, tmp_path):
    """Simple upload to a specific name different from metadata, success result."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload.return_value = store_response

    test_charm = tmp_path / "mystuff.charm"
    _build_zip_with_yaml(test_charm, "metadata.yaml", content={"name": "mycharm"})
    args = Namespace(filepath=test_charm, release=[], name="foo-mycharm", format=False)
    retcode = UploadCommand(config).run(args)
    assert retcode == 0

    assert store_mock.mock_calls == [call.upload("foo-mycharm", test_charm)]
    expected = "Revision 7 of 'foo-mycharm' created"
    emitter.assert_message(expected)


# -- tests for list revisions command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_simple(emitter, store_mock, config, formatted):
    """Happy path of one result from the Store."""
    bases = [Base(architecture="amd64", channel="20.04", name="ubuntu")]
    store_response = [
        Revision(
            revision=1,
            version="v1",
            created_at=datetime.datetime(2020, 7, 3, 20, 30, 40),
            status="accepted",
            errors=[],
            bases=bases,
        ),
    ]
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_revisions("testcharm"),
    ]
    if formatted:
        expected = [
            {
                "revision": 1,
                "version": "v1",
                "created_at": "2020-07-03T20:30:40Z",
                "status": "accepted",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Version    Created at            Status",
            "1           v1         2020-07-03T20:30:40Z  accepted",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_empty(emitter, store_mock, config, formatted):
    """No results from the store."""
    store_response = []
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    if formatted:
        emitter.assert_json_output([])
    else:
        expected = [
            "No revisions found.",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_ordered_by_revision(emitter, store_mock, config, formatted):
    """Results are presented ordered by revision in the table."""
    # three Revisions with all values weirdly similar, the only difference is revision, so
    # we really assert later that it was used for ordering
    tstamp = datetime.datetime(2020, 7, 3, 20, 30, 40)
    bases = [Base(architecture="amd64", channel="20.04", name="ubuntu")]
    store_response = [
        Revision(
            revision=1,
            version="v1",
            created_at=tstamp,
            status="accepted",
            errors=[],
            bases=bases,
        ),
        Revision(
            revision=3,
            version="v1",
            created_at=tstamp,
            status="accepted",
            errors=[],
            bases=bases,
        ),
        Revision(
            revision=2,
            version="v1",
            created_at=tstamp,
            status="accepted",
            errors=[],
            bases=bases,
        ),
    ]
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 3,
                "version": "v1",
                "created_at": "2020-07-03T20:30:40Z",
                "status": "accepted",
            },
            {
                "revision": 2,
                "version": "v1",
                "created_at": "2020-07-03T20:30:40Z",
                "status": "accepted",
            },
            {
                "revision": 1,
                "version": "v1",
                "created_at": "2020-07-03T20:30:40Z",
                "status": "accepted",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Version    Created at            Status",
            "3           v1         2020-07-03T20:30:40Z  accepted",
            "2           v1         2020-07-03T20:30:40Z  accepted",
            "1           v1         2020-07-03T20:30:40Z  accepted",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_version_null(emitter, store_mock, config, formatted):
    """Support the case of version being None."""
    bases = [Base(architecture="amd64", channel="20.04", name="ubuntu")]
    store_response = [
        Revision(
            revision=1,
            version=None,
            created_at=datetime.datetime(2020, 7, 3, 20, 30, 40),
            status="accepted",
            errors=[],
            bases=bases,
        ),
    ]
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 1,
                "version": None,
                "created_at": "2020-07-03T20:30:40Z",
                "status": "accepted",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Version    Created at            Status",
            "1                      2020-07-03T20:30:40Z  accepted",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_errors_simple(emitter, store_mock, config, formatted):
    """Support having one case with a simple error."""
    bases = [Base(architecture="amd64", channel="20.04", name="ubuntu")]
    store_response = [
        Revision(
            revision=1,
            version=None,
            created_at=datetime.datetime(2020, 7, 3, 20, 30, 40),
            status="rejected",
            errors=[Error(message="error text", code="broken")],
            bases=bases,
        ),
    ]
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 1,
                "version": None,
                "created_at": "2020-07-03T20:30:40Z",
                "status": "rejected",
                "errors": [{"message": "error text", "code": "broken"}],
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Version    Created at            Status",
            "1                      2020-07-03T20:30:40Z  rejected: error text [broken]",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_revisions_errors_multiple(emitter, store_mock, config, formatted):
    """Support having one case with multiple errors."""
    bases = [Base(architecture="amd64", channel="20.04", name="ubuntu")]
    store_response = [
        Revision(
            revision=1,
            version=None,
            created_at=datetime.datetime(2020, 7, 3, 20, 30, 40),
            status="rejected",
            errors=[
                Error(message="text 1", code="missing-stuff"),
                Error(message="other long error text", code="broken"),
            ],
            bases=bases,
        ),
    ]
    store_mock.list_revisions.return_value = store_response

    args = Namespace(name="testcharm", format=formatted)
    ListRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 1,
                "version": None,
                "created_at": "2020-07-03T20:30:40Z",
                "status": "rejected",
                "errors": [
                    {"message": "text 1", "code": "missing-stuff"},
                    {"message": "other long error text", "code": "broken"},
                ],
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Version    Created at            Status",
            "1                      2020-07-03T20:30:40Z  rejected: text 1 [missing-stuff]; other long error text [broken]",
        ]
        emitter.assert_messages(expected)


# -- tests for the release command


def test_release_simple_ok(emitter, store_mock, config):
    """Simple case of releasing a revision ok."""
    channels = ["somechannel"]
    args = Namespace(name="testcharm", revision=7, channel=channels, resource=[])
    ReleaseCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.release("testcharm", 7, channels, []),
    ]

    expected = "Revision 7 of 'testcharm' released to somechannel"
    emitter.assert_message(expected)


def test_release_simple_multiple_channels(emitter, store_mock, config):
    """Releasing to multiple channels."""
    args = Namespace(
        name="testcharm",
        revision=7,
        channel=["channel1", "channel2", "channel3"],
        resource=[],
    )
    ReleaseCommand(config).run(args)

    expected = "Revision 7 of 'testcharm' released to channel1, channel2, channel3"
    emitter.assert_message(expected)


def test_release_including_resources(emitter, store_mock, config):
    """Releasing with resources."""
    r1 = ResourceOption(name="foo", revision=3)
    r2 = ResourceOption(name="bar", revision=17)
    args = Namespace(name="testcharm", revision=7, channel=["testchannel"], resource=[r1, r2])
    ReleaseCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.release("testcharm", 7, ["testchannel"], [r1, r2]),
    ]

    expected = (
        "Revision 7 of 'testcharm' released to testchannel "
        "(attaching resources: 'foo' r3, 'bar' r17)"
    )
    emitter.assert_message(expected)


def test_release_options_resource(config):
    """The --resource-file option implies a set of validations."""
    cmd = ReleaseCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "resource")
    assert isinstance(action.type, ResourceOption)


@pytest.mark.parametrize(
    ("sysargs", "expected_parsed"),
    [
        (
            ["somename", "--channel=stable", "--revision=33"],
            ("somename", 33, ["stable"], []),
        ),
        (
            ["somename", "--channel=stable", "-r", "33"],
            ("somename", 33, ["stable"], []),
        ),
        (
            ["somename", "-c", "stable", "--revision=33"],
            ("somename", 33, ["stable"], []),
        ),
        (
            ["-c", "stable", "--revision=33", "somename"],
            ("somename", 33, ["stable"], []),
        ),
        (
            ["-c", "beta", "--revision=1", "--channel=edge", "name"],
            ("name", 1, ["beta", "edge"], []),
        ),
        (
            ["somename", "-c=beta", "-r=3", "--resource=foo:15"],
            ("somename", 3, ["beta"], [ResourceOption("foo", 15)]),
        ),
        (
            ["somename", "-c=beta", "-r=3", "--resource=foo:15", "--resource=bar:99"],
            (
                "somename",
                3,
                ["beta"],
                [ResourceOption("foo", 15), ResourceOption("bar", 99)],
            ),
        ),
    ],
)
def test_release_parameters_ok(config, sysargs, expected_parsed):
    """Control of different combination of valid parameters."""
    cmd = ReleaseCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    try:
        args = parser.parse_args(sysargs)
    except SystemExit:
        pytest.fail(f"Parsing of {sysargs} was not ok.")
    attribs = ["name", "revision", "channel", "resource"]
    assert args == Namespace(**dict(zip(attribs, expected_parsed)))


@pytest.mark.parametrize(
    "sysargs",
    [
        ["somename", "--channel=stable", "--revision=foo"],  # revision not an int
        ["somename", "--channel=stable"],  # missing the revision
        ["somename", "--revision=1"],  # missing a channel
        [
            "somename",
            "--channel=stable",
            "--revision=1",
            "--revision=2",
        ],  # too many revisions
        ["--channel=stable", "--revision=1"],  # missing the name
        ["somename", "-c=beta", "-r=3", "--resource=foo15"],  # bad resource format
    ],
)
def test_release_parameters_bad(config, sysargs):
    """Control of different option/parameters combinations that are not valid."""
    cmd = ReleaseCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(sysargs)


# -- tests for the close command


def test_close_simple_ok(emitter, store_mock, config):
    """Simple case of closing a channel."""
    args = Namespace(name="testcharm", channel="somechannel")
    CloseCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.release("testcharm", None, ["somechannel"], []),
    ]

    expected = "Closed 'somechannel' channel for 'testcharm'."
    emitter.assert_message(expected)


# -- tests for the status command


def _build_channels(track="latest"):
    """Helper to build simple channels structure."""
    channels = []
    risks = ["stable", "candidate", "beta", "edge"]
    for risk, fback in zip(risks, [None, *risks]):
        name = "/".join((track, risk))
        fallback = None if fback is None else "/".join((track, fback))
        channels.append(Channel(name=name, fallback=fallback, track=track, risk=risk, branch=None))
    return channels


def _build_revision(revno, version):
    """Helper to build a revision."""
    return Revision(
        revision=revno,
        version=version,
        created_at=datetime.datetime(2020, 7, 3, 20, 30, 40),
        status="accepted",
        errors=[],
        bases=[Base(architecture="amd64", channel="20.04", name="ubuntu")],
    )


def _build_release(revision, channel, expires_at=None, resources=None, base=DEFAULT):
    """Helper to build a release."""
    if resources is None:
        resources = []
    if base is DEFAULT:
        base = Base(architecture="amd64", channel="20.04", name="ubuntu")
    return Release(
        revision=revision,
        channel=channel,
        expires_at=expires_at,
        resources=resources,
        base=base,
    )


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_simple_ok(emitter, store_mock, config, formatted):
    """Simple happy case of getting a status."""
    channel_map = [
        _build_release(revision=7, channel="latest/stable"),
        _build_release(revision=7, channel="latest/candidate"),
        _build_release(revision=80, channel="latest/beta"),
        _build_release(revision=156, channel="latest/edge"),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=7, version="v7"),
        _build_revision(revno=80, version="2.0"),
        _build_revision(revno=156, version="git-0db35ea1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "open",
                                "channel": "latest/stable",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/candidate",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta",
                                "version": "2.0",
                                "revision": 80,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/edge",
                                "version": "git-0db35ea1",
                                "revision": 156,
                                "resources": [],
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version       Revision",
            "latest   ubuntu 20.04 (amd64)  stable     v7            7",
            "                               candidate  v7            7",
            "                               beta       2.0           80",
            "                               edge       git-0db35ea1  156",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_empty(emitter, store_mock, config, formatted):
    """Empty response from the store."""
    store_mock.list_releases.return_value = [], [], []
    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    if formatted:
        emitter.assert_json_output({})
    else:
        expected = "Nothing has been released yet."
        emitter.assert_message(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_channels_not_released_with_fallback(emitter, store_mock, config, formatted):
    """Support gaps in channel releases, having fallbacks."""
    channel_map = [
        _build_release(revision=7, channel="latest/stable"),
        _build_release(revision=80, channel="latest/edge"),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=7, version="v7"),
        _build_revision(revno=80, version="2.0"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "open",
                                "channel": "latest/stable",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/beta",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/edge",
                                "version": "2.0",
                                "revision": 80,
                                "resources": [],
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version    Revision",
            "latest   ubuntu 20.04 (amd64)  stable     v7         7",
            "                               candidate  ↑          ↑",
            "                               beta       ↑          ↑",
            "                               edge       2.0        80",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_channels_not_released_without_fallback(emitter, store_mock, config, formatted):
    """Support gaps in channel releases, nothing released in more stable ones."""
    channel_map = [
        _build_release(revision=5, channel="latest/beta"),
        _build_release(revision=12, channel="latest/edge"),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=5, version="5.1"),
        _build_revision(revno=12, version="almostready"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "closed",
                                "channel": "latest/stable",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "closed",
                                "channel": "latest/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta",
                                "version": "5.1",
                                "revision": 5,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/edge",
                                "version": "almostready",
                                "revision": 12,
                                "resources": [],
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version      Revision",
            "latest   ubuntu 20.04 (amd64)  stable     -            -",
            "                               candidate  -            -",
            "                               beta       5.1          5",
            "                               edge       almostready  12",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_multiple_tracks(emitter, store_mock, config, formatted):
    """Support multiple tracks."""
    channel_map = [
        _build_release(revision=503, channel="latest/stable"),
        _build_release(revision=1, channel="2.0/edge"),
    ]
    channels_latest = _build_channels()
    channels_track = _build_channels(track="2.0")
    channels = channels_latest + channels_track
    revisions = [
        _build_revision(revno=503, version="7.5.3"),
        _build_revision(revno=1, version="1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "open",
                                "channel": "latest/stable",
                                "version": "7.5.3",
                                "revision": 503,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/beta",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/edge",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            },
            {
                "track": "2.0",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "closed",
                                "channel": "2.0/stable",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "closed",
                                "channel": "2.0/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "closed",
                                "channel": "2.0/beta",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "2.0/edge",
                                "version": "1",
                                "revision": 1,
                                "resources": [],
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version    Revision",
            "latest   ubuntu 20.04 (amd64)  stable     7.5.3      503",
            "                               candidate  ↑          ↑",
            "                               beta       ↑          ↑",
            "                               edge       ↑          ↑",
            "2.0      ubuntu 20.04 (amd64)  stable     -          -",
            "                               candidate  -          -",
            "                               beta       -          -",
            "                               edge       1          1",
        ]
        emitter.assert_messages(expected)


def test_status_tracks_order(emitter, store_mock, config):
    """Respect the track ordering from the store."""
    channel_map = [
        _build_release(revision=1, channel="latest/edge"),
        _build_release(revision=2, channel="aaa/edge"),
        _build_release(revision=3, channel="2.0/edge"),
        _build_release(revision=4, channel="zzz/edge"),
    ]
    channels_latest = _build_channels()
    channels_track_1 = _build_channels(track="zzz")
    channels_track_2 = _build_channels(track="2.0")
    channels_track_3 = _build_channels(track="aaa")
    channels = channels_latest + channels_track_1 + channels_track_2 + channels_track_3
    revisions = [
        _build_revision(revno=1, version="v1"),
        _build_revision(revno=2, version="v2"),
        _build_revision(revno=3, version="v3"),
        _build_revision(revno=4, version="v4"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel    Version    Revision",
        "latest   ubuntu 20.04 (amd64)  stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v1         1",
        "zzz      ubuntu 20.04 (amd64)  stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v4         4",
        "2.0      ubuntu 20.04 (amd64)  stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v3         3",
        "aaa      ubuntu 20.04 (amd64)  stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v2         2",
    ]
    emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_with_one_branch(emitter, store_mock, config, formatted):
    """Support having one branch."""
    tstamp_with_timezone = dateutil.parser.parse("2020-07-03T20:30:40Z")
    channel_map = [
        _build_release(revision=5, channel="latest/beta"),
        _build_release(
            revision=12,
            channel="latest/beta/mybranch",
            expires_at=tstamp_with_timezone,
        ),
    ]
    channels = _build_channels()
    channels.append(
        Channel(
            name="latest/beta/mybranch",
            fallback="latest/beta",
            track="latest",
            risk="beta",
            branch="mybranch",
        )
    )
    revisions = [
        _build_revision(revno=5, version="5.1"),
        _build_revision(revno=12, version="ver.12"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "closed",
                                "channel": "latest/stable",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "closed",
                                "channel": "latest/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta",
                                "version": "5.1",
                                "revision": 5,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/edge",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta/mybranch",
                                "version": "ver.12",
                                "revision": 12,
                                "resources": [],
                                "expires_at": "2020-07-03T20:30:40Z",
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel        Version    Revision    Expires at",
            "latest   ubuntu 20.04 (amd64)  stable         -          -",
            "                               candidate      -          -",
            "                               beta           5.1        5",
            "                               edge           ↑          ↑",
            "                               beta/mybranch  ver.12     12          2020-07-03T20:30:40Z",
        ]
        emitter.assert_messages(expected)


def test_status_with_multiple_branches(emitter, store_mock, config):
    """Support having multiple branches."""
    tstamp = dateutil.parser.parse("2020-07-03T20:30:40Z")
    channel_map = [
        _build_release(revision=5, channel="latest/beta"),
        _build_release(revision=12, channel="latest/beta/branch-1", expires_at=tstamp),
        _build_release(revision=15, channel="latest/beta/branch-2", expires_at=tstamp),
    ]
    channels = _build_channels()
    channels.extend(
        [
            Channel(
                name="latest/beta/branch-1",
                fallback="latest/beta",
                track="latest",
                risk="beta",
                branch="branch-1",
            ),
            Channel(
                name="latest/beta/branch-2",
                fallback="latest/beta",
                track="latest",
                risk="beta",
                branch="branch-2",
            ),
        ]
    )
    revisions = [
        _build_revision(revno=5, version="5.1"),
        _build_revision(revno=12, version="ver.12"),
        _build_revision(revno=15, version="15.0.0"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel        Version    Revision    Expires at",
        "latest   ubuntu 20.04 (amd64)  stable         -          -",
        "                               candidate      -          -",
        "                               beta           5.1        5",
        "                               edge           ↑          ↑",
        "                               beta/branch-1  ver.12     12          2020-07-03T20:30:40Z",
        "                               beta/branch-2  15.0.0     15          2020-07-03T20:30:40Z",
    ]
    emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_with_resources(emitter, store_mock, config, formatted):
    """Support having multiple branches."""
    res1 = Resource(name="resource1", optional=True, revision=1, resource_type="file")
    res2 = Resource(name="resource2", optional=True, revision=54, resource_type="file")
    channel_map = [
        _build_release(revision=5, channel="latest/candidate", resources=[res1, res2]),
        _build_release(revision=5, channel="latest/beta", resources=[res1]),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=5, version="5.1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "closed",
                                "channel": "latest/stable",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/candidate",
                                "version": "5.1",
                                "revision": 5,
                                "resources": [
                                    {"name": "resource1", "revision": 1},
                                    {"name": "resource2", "revision": 54},
                                ],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta",
                                "version": "5.1",
                                "revision": 5,
                                "resources": [{"name": "resource1", "revision": 1}],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/edge",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version    Revision    Resources",
            "latest   ubuntu 20.04 (amd64)  stable     -          -           -",
            "                               candidate  5.1        5           resource1 (r1), resource2 (r54)",
            "                               beta       5.1        5           resource1 (r1)",
            "                               edge       ↑          ↑           ↑",
        ]
        emitter.assert_messages(expected)


def test_status_with_resources_missing_after_closed_channel(emitter, store_mock, config):
    """Specific glitch for a channel without resources after a closed one."""
    resource = Resource(name="resource", optional=True, revision=1, resource_type="file")
    channel_map = [
        _build_release(revision=5, channel="latest/stable", resources=[resource]),
        _build_release(revision=5, channel="latest/beta", resources=[]),
        _build_release(revision=5, channel="latest/edge", resources=[resource]),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=5, version="5.1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    expected = [
        "Track    Base                  Channel    Version    Revision    Resources",
        "latest   ubuntu 20.04 (amd64)  stable     5.1        5           resource (r1)",
        "                               candidate  ↑          ↑           ↑",
        "                               beta       5.1        5           -",
        "                               edge       5.1        5           resource (r1)",
    ]
    emitter.assert_messages(expected)


def test_status_with_resources_and_branches(emitter, store_mock, config):
    """Support having multiple branches."""
    tstamp = dateutil.parser.parse("2020-07-03T20:30:40Z")
    res1 = Resource(name="testres", optional=True, revision=1, resource_type="file")
    res2 = Resource(name="testres", optional=True, revision=14, resource_type="file")
    channel_map = [
        _build_release(revision=23, channel="latest/beta", resources=[res2]),
        _build_release(
            revision=5,
            channel="latest/edge/mybranch",
            expires_at=tstamp,
            resources=[res1],
        ),
    ]
    channels = _build_channels()
    channels.append(
        Channel(
            name="latest/edge/mybranch",
            fallback="latest/edge",
            track="latest",
            risk="edge",
            branch="mybranch",
        )
    )
    revisions = [
        _build_revision(revno=5, version="5.1"),
        _build_revision(revno=23, version="7.0.0"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    expected = [
        "Track    Base                  Channel        Version    Revision    Resources      Expires at",
        "latest   ubuntu 20.04 (amd64)  stable         -          -           -",
        "                               candidate      -          -           -",
        "                               beta           7.0.0      23          testres (r14)",
        "                               edge           ↑          ↑           ↑",
        "                               edge/mybranch  5.1        5           testres (r1)   2020-07-03T20:30:40Z",
    ]
    emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_multiplebases_single_track(emitter, store_mock, config, formatted):
    """Multiple bases with one track."""
    other_base = Base(architecture="16b", channel="1", name="xz")
    channel_map = [
        _build_release(revision=7, channel="latest/stable", base=other_base),
        _build_release(revision=7, channel="latest/candidate"),
        _build_release(revision=80, channel="latest/beta", base=other_base),
        _build_release(revision=156, channel="latest/edge"),
    ]
    channels = _build_channels()
    revisions = [
        _build_revision(revno=7, version="v7"),
        _build_revision(revno=80, version="2.0"),
        _build_revision(revno=156, version="git-0db35ea1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": {
                            "name": "ubuntu",
                            "channel": "20.04",
                            "architecture": "amd64",
                        },
                        "releases": [
                            {
                                "status": "closed",
                                "channel": "latest/stable",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/candidate",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/beta",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/edge",
                                "version": "git-0db35ea1",
                                "revision": 156,
                                "resources": [],
                                "expires_at": None,
                            },
                        ],
                    },
                    {
                        "base": {
                            "name": "xz",
                            "channel": "1",
                            "architecture": "16b",
                        },
                        "releases": [
                            {
                                "status": "open",
                                "channel": "latest/stable",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/candidate",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/beta",
                                "version": "2.0",
                                "revision": 80,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/edge",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base                  Channel    Version       Revision",
            "latest   ubuntu 20.04 (amd64)  stable     -             -",
            "                               candidate  v7            7",
            "                               beta       ↑             ↑",
            "                               edge       git-0db35ea1  156",
            "         xz 1 (16b)            stable     v7            7",
            "                               candidate  ↑             ↑",
            "                               beta       2.0           80",
            "                               edge       ↑             ↑",
        ]
        emitter.assert_messages(expected)


def test_status_multiplebases_multiple_tracks(emitter, store_mock, config):
    """Multiple bases with several tracks."""
    other_base = Base(architecture="16b", channel="1", name="xz")
    channel_map = [
        _build_release(revision=7, channel="latest/stable", base=other_base),
        _build_release(revision=7, channel="latest/candidate"),
        _build_release(revision=80, channel="latest/beta", base=other_base),
        _build_release(revision=156, channel="latest/edge"),
        _build_release(revision=7, channel="2.0/stable", base=other_base),
        _build_release(revision=7, channel="2.0/candidate"),
        _build_release(revision=80, channel="2.0/beta", base=other_base),
        _build_release(revision=156, channel="2.0/edge"),
        _build_release(revision=156, channel="3.0/edge"),
    ]
    channels = _build_channels() + _build_channels(track="2.0") + _build_channels(track="3.0")
    revisions = [
        _build_revision(revno=7, version="v7"),
        _build_revision(revno=80, version="2.0"),
        _build_revision(revno=156, version="git-0db35ea1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel    Version       Revision",
        "latest   ubuntu 20.04 (amd64)  stable     -             -",
        "                               candidate  v7            7",
        "                               beta       ↑             ↑",
        "                               edge       git-0db35ea1  156",
        "         xz 1 (16b)            stable     v7            7",
        "                               candidate  ↑             ↑",
        "                               beta       2.0           80",
        "                               edge       ↑             ↑",
        "2.0      ubuntu 20.04 (amd64)  stable     -             -",
        "                               candidate  v7            7",
        "                               beta       ↑             ↑",
        "                               edge       git-0db35ea1  156",
        "         xz 1 (16b)            stable     v7            7",
        "                               candidate  ↑             ↑",
        "                               beta       2.0           80",
        "                               edge       ↑             ↑",
        "3.0      ubuntu 20.04 (amd64)  stable     -             -",
        "                               candidate  -             -",
        "                               beta       -             -",
        "                               edge       git-0db35ea1  156",
    ]
    emitter.assert_messages(expected)


def test_status_multiplebases_everything_combined(emitter, store_mock, config):
    """Validate multiple bases with several other modifiers."""
    other_base = Base(architecture="16b", channel="1", name="xz")
    tstamp = dateutil.parser.parse("2020-07-03T20:30:40Z")
    resource = Resource(name="testres", optional=True, revision=1, resource_type="file")
    channel_map = [
        _build_release(revision=7, channel="latest/candidate"),
        _build_release(revision=156, channel="latest/edge"),
        _build_release(revision=7, channel="latest/candidate/br1", expires_at=tstamp),
        _build_release(revision=7, channel="latest/stable", base=other_base),
        _build_release(revision=80, channel="latest/beta", base=other_base),
        _build_release(
            revision=99,
            channel="latest/beta/br2",
            base=other_base,
            expires_at=tstamp,
            resources=[resource],
        ),
        _build_release(revision=7, channel="2.0/candidate"),
        _build_release(revision=80, channel="2.0/beta"),
        _build_release(revision=7, channel="2.0/stable", base=other_base),
        _build_release(revision=80, channel="2.0/edge", base=other_base),
        _build_release(revision=80, channel="2.0/edge/foobar", base=other_base, expires_at=tstamp),
    ]
    channels = _build_channels() + _build_channels(track="2.0")
    channels.extend(
        [
            Channel(
                name="latest/candidate/br1",
                fallback="latest/candidate",
                track="latest",
                risk="candidate",
                branch="br1",
            ),
            Channel(
                name="latest/beta/br2",
                fallback="latest/beta",
                track="latest",
                risk="beta",
                branch="br2",
            ),
            Channel(
                name="2.0/edge/foobar",
                fallback="2.0/edge",
                track="2.0",
                risk="edge",
                branch="foobar",
            ),
        ]
    )
    revisions = [
        _build_revision(revno=7, version="v7"),
        _build_revision(revno=80, version="2.0"),
        _build_revision(revno=156, version="git-0db35ea1"),
        _build_revision(revno=99, version="weird"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel        Version       Revision    Resources     Expires at",
        "latest   ubuntu 20.04 (amd64)  stable         -             -           -",
        "                               candidate      v7            7           -",
        "                               beta           ↑             ↑           ↑",
        "                               edge           git-0db35ea1  156         -",
        "                               candidate/br1  v7            7           -             2020-07-03T20:30:40Z",
        "         xz 1 (16b)            stable         v7            7           -",
        "                               candidate      ↑             ↑           ↑",
        "                               beta           2.0           80          -",
        "                               edge           ↑             ↑           ↑",
        "                               beta/br2       weird         99          testres (r1)  2020-07-03T20:30:40Z",
        "2.0      ubuntu 20.04 (amd64)  stable         -             -           -",
        "                               candidate      v7            7           -",
        "                               beta           2.0           80          -",
        "                               edge           ↑             ↑           ↑",
        "         xz 1 (16b)            stable         v7            7           -",
        "                               candidate      ↑             ↑           ↑",
        "                               beta           ↑             ↑           ↑",
        "                               edge           2.0           80          -",
        "                               edge/foobar    2.0           80          -             2020-07-03T20:30:40Z",
    ]
    emitter.assert_messages(expected)


def test_status_multiplebases_multiplebranches(emitter, store_mock, config):
    """Validate specific mix between bases and branches.

    This exposes a bug in Charmhub: https://bugs.launchpad.net/snapstore-server/+bug/1994613
    """
    other_base = Base(architecture="i386", channel="20.04", name="ubuntu")
    tstamp = dateutil.parser.parse("2020-07-03T20:30:40Z")
    channel_map = [
        _build_release(revision=1, channel="latest/edge"),
        _build_release(revision=1, channel="latest/edge/fix", expires_at=tstamp),
        _build_release(revision=1, channel="latest/edge", base=other_base),
        _build_release(revision=1, channel="latest/edge/fix", expires_at=tstamp, base=other_base),
    ]
    channels = _build_channels()
    extra_channel = Channel(
        name="latest/edge/fix",
        fallback="latest/edge",
        track="latest",
        risk="edge",
        branch="fix",
    )
    channels.extend([extra_channel, extra_channel])  # twice!! this is the reported bug in Charmhub
    revisions = [
        _build_revision(revno=1, version="v1"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel    Version    Revision    Expires at",
        "latest   ubuntu 20.04 (amd64)  stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v1         1",
        "                               edge/fix   v1         1           2020-07-03T20:30:40Z",
        "         ubuntu 20.04 (i386)   stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       v1         1",
        "                               edge/fix   v1         1           2020-07-03T20:30:40Z",
    ]
    emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_status_with_base_in_none(emitter, store_mock, config, formatted):
    """Support the case of base being None."""
    channel_map = [
        _build_release(revision=7, channel="latest/stable", base=None),
        _build_release(revision=7, channel="latest/candidate", base=None),
    ]
    channels = _build_channels()
    revisions = [_build_revision(revno=7, version="v7")]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=formatted)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    if formatted:
        expected = [
            {
                "track": "latest",
                "mappings": [
                    {
                        "base": None,
                        "releases": [
                            {
                                "status": "open",
                                "channel": "latest/stable",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "open",
                                "channel": "latest/candidate",
                                "version": "v7",
                                "revision": 7,
                                "resources": [],
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/beta",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                            {
                                "status": "tracking",
                                "channel": "latest/edge",
                                "version": None,
                                "revision": None,
                                "resources": None,
                                "expires_at": None,
                            },
                        ],
                    },
                ],
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Track    Base    Channel    Version    Revision",
            "latest   -       stable     v7         7",
            "                 candidate  v7         7",
            "                 beta       ↑          ↑",
            "                 edge       ↑          ↑",
        ]
        emitter.assert_messages(expected)


def test_status_unreleased_track(emitter, store_mock, config):
    """The package has a track, but nothing is released to it."""
    channel_map = [
        _build_release(revision=5, channel="latest/stable"),
    ]
    channels_latest = _build_channels()
    channels_track = _build_channels(track="2.0")
    channels = channels_latest + channels_track
    revisions = [
        _build_revision(revno=5, version="7.5.3"),
    ]
    store_mock.list_releases.return_value = (channel_map, channels, revisions)

    args = Namespace(name="testcharm", format=False)
    StatusCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_releases("testcharm"),
    ]

    expected = [
        "Track    Base                  Channel    Version    Revision",
        "latest   ubuntu 20.04 (amd64)  stable     7.5.3      5",
        "                               candidate  ↑          ↑",
        "                               beta       ↑          ↑",
        "                               edge       ↑          ↑",
        "2.0      -                     stable     -          -",
        "                               candidate  -          -",
        "                               beta       -          -",
        "                               edge       -          -",
    ]
    emitter.assert_messages(expected)


# -- tests for create library command


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
@pytest.mark.parametrize("charmcraft_yaml_name", [None, "test-charm"])
def test_createlib_simple(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted, charmcraft_yaml_name
):
    """Happy path with result from the Store."""
    if not charmcraft_yaml_name:
        pytest.xfail("Store commands need refactoring to not need a project.")
    monkeypatch.chdir(tmp_path)

    config.name = charmcraft_yaml_name

    lib_id = "test-example-lib-id"
    store_mock.create_library_id.return_value = lib_id

    args = Namespace(name="testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        CreateLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.create_library_id("test-charm", "testlib"),
    ]
    if formatted:
        expected = {"library_id": lib_id}
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Library charms.test_charm.v0.testlib created with id test-example-lib-id.",
            "Consider 'git add lib/charms/test_charm/v0/testlib.py'.",
        ]
        emitter.assert_messages(expected)
    created_lib_file = tmp_path / "lib" / "charms" / "test_charm" / "v0" / "testlib.py"

    env = get_templates_environment("charmlibs")
    expected_newlib_content = env.get_template("new_library.py.j2").render(lib_id=lib_id)
    assert created_lib_file.read_text() == expected_newlib_content


@pytest.mark.xfail(
    strict=True, raises=pydantic.ValidationError, reason="Store commands need refactor."
)
def test_createlib_name_from_metadata_problem(store_mock, config):
    """The metadata wasn't there to get the name."""
    args = Namespace(name="testlib", format=None)
    config.name = None
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = None
        with pytest.raises(CraftError) as cm:
            CreateLibCommand(config).run(args)
        assert str(cm.value) == (
            "Cannot find a valid charm name in charm definition. "
            "Check that you are using the correct project directory."
        )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_createlib_name_contains_dash(emitter, store_mock, tmp_path, monkeypatch, config):
    """'-' is valid in charm names but can't be imported"""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    store_mock.create_library_id.return_value = lib_id

    args = Namespace(name="testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        CreateLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.create_library_id("test-charm", "testlib"),
    ]
    expected = [
        "Library charms.test_charm.v0.testlib created with id test-example-lib-id.",
        "Consider 'git add lib/charms/test_charm/v0/testlib.py'.",
    ]
    emitter.assert_messages(expected)
    created_lib_file = tmp_path / "lib" / "charms" / "test_charm" / "v0" / "testlib.py"

    env = get_templates_environment("charmlibs")
    expected_newlib_content = env.get_template("new_library.py.j2").render(lib_id=lib_id)
    assert created_lib_file.read_text() == expected_newlib_content


@pytest.mark.parametrize(
    "lib_name",
    [
        "foo.bar",
        "foo/bar",
        "Foo",
        "123foo",
        "_foo",
        "",
    ],
)
def test_createlib_invalid_name(lib_name, config):
    """Verify that it cannot be used with an invalid name."""
    args = Namespace(name=lib_name, format=None)
    with pytest.raises(CraftError) as err:
        CreateLibCommand(config).run(args)
    assert str(err.value) == (
        "Invalid library name. Must only use lowercase alphanumeric "
        "characters and underscore, starting with alpha."
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_createlib_path_already_there(tmp_path, monkeypatch, config):
    """The intended-to-be-created library is already there."""
    monkeypatch.chdir(tmp_path)

    factory.create_lib_filepath("test-charm", "testlib", api=0)
    args = Namespace(name="testlib", format=None)
    with pytest.raises(CraftError) as err:
        CreateLibCommand(config).run(args)

    assert str(err.value) == (
        "This library already exists: 'lib/charms/test_charm/v0/testlib.py'."
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_createlib_path_can_not_write(tmp_path, monkeypatch, store_mock, add_cleanup, config):
    """Disk error when trying to write the new lib (bad permissions, name too long, whatever)."""
    lib_dir = tmp_path / "lib" / "charms" / "test_charm" / "v0"
    lib_dir.mkdir(parents=True)
    lib_dir.chmod(0o111)
    add_cleanup(lib_dir.chmod, 0o777)
    monkeypatch.chdir(tmp_path)

    args = Namespace(name="testlib", format=None)
    store_mock.create_library_id.return_value = "lib_id"
    expected_error = "Error writing the library in .*: PermissionError.*"
    with pytest.raises(CraftError, match=expected_error):
        CreateLibCommand(config).run(args)


def test_createlib_library_template_is_python(emitter, store_mock, tmp_path, monkeypatch):
    """Verify that the template used to create a library is valid Python code."""
    env = get_templates_environment("charmlibs")
    newlib_content = env.get_template("new_library.py.j2").render(lib_id="test-lib-id")
    compile(newlib_content, "test.py", "exec")


# -- tests for publish libraries command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_simple(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Happy path publishing because no revision at all in the Store."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "test-charm", "testlib", api=0, patch=1, lib_id=lib_id
    )

    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "testcharm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
        call.create_library_revision("test-charm", lib_id, 0, 1, content, content_hash),
    ]
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "published": {
                    "patch": 1,
                    "content_hash": content_hash,
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = "Library charms.test_charm.v0.testlib sent to the store with version 0.1"
        emitter.assert_message(expected)


def test_publishlib_contains_dash(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path publishing because no revision at all in the Store."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "test-charm", "testlib", api=0, patch=1, lib_id=lib_id
    )

    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(library="charms.test_charm.v0.testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
        call.create_library_revision("test-charm", lib_id, 0, 1, content, content_hash),
    ]
    expected = "Library charms.test_charm.v0.testlib sent to the store with version 0.1"
    emitter.assert_message(expected)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_all(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Publish all the libraries found in disk."""
    monkeypatch.chdir(tmp_path)
    config.name = "testcharm-1"

    c1, h1 = factory.create_lib_filepath(
        "testcharm-1", "testlib-a", api=0, patch=1, lib_id="lib_id_1"
    )
    c2, h2 = factory.create_lib_filepath(
        "testcharm-1", "testlib-b", api=0, patch=1, lib_id="lib_id_2"
    )
    c3, h3 = factory.create_lib_filepath(
        "testcharm-1", "testlib-b", api=1, patch=3, lib_id="lib_id_2"
    )
    factory.create_lib_filepath("testcharm-2", "testlib", api=0, patch=1, lib_id="lib_id_4")

    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(library=None, format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "testcharm-1"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips(
            [
                {"lib_id": "lib_id_1", "api": 0},
                {"lib_id": "lib_id_2", "api": 0},
                {"lib_id": "lib_id_2", "api": 1},
            ]
        ),
        call.create_library_revision("testcharm-1", "lib_id_1", 0, 1, c1, h1),
        call.create_library_revision("testcharm-1", "lib_id_2", 0, 1, c2, h2),
        call.create_library_revision("testcharm-1", "lib_id_2", 1, 3, c3, h3),
    ]
    names = [
        "charms.testcharm_1.v0.testlib-a",
        "charms.testcharm_1.v0.testlib-b",
        "charms.testcharm_1.v1.testlib-b",
    ]
    emitter.assert_debug("Libraries found under 'lib/charms/testcharm_1': " + str(names))
    if formatted:
        expected = [
            {
                "charm_name": "testcharm-1",
                "library_name": "testlib-a",
                "library_id": "lib_id_1",
                "api": 0,
                "published": {
                    "patch": 1,
                    "content_hash": h1,
                },
            },
            {
                "charm_name": "testcharm-1",
                "library_name": "testlib-b",
                "library_id": "lib_id_2",
                "api": 0,
                "published": {
                    "patch": 1,
                    "content_hash": h2,
                },
            },
            {
                "charm_name": "testcharm-1",
                "library_name": "testlib-b",
                "library_id": "lib_id_2",
                "api": 1,
                "published": {
                    "patch": 3,
                    "content_hash": h3,
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(
            [
                "Library charms.testcharm_1.v0.testlib-a sent to the store with version 0.1",
                "Library charms.testcharm_1.v0.testlib-b sent to the store with version 0.1",
                "Library charms.testcharm_1.v1.testlib-b sent to the store with version 1.3",
            ]
        )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_publishlib_not_found(emitter, store_mock, tmp_path, monkeypatch, config):
    """The indicated library is not found."""
    monkeypatch.chdir(tmp_path)

    args = Namespace(library="charms.testcharm.v0.testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "testcharm"
        with pytest.raises(CraftError) as cm:
            PublishLibCommand(config).run(args)

        assert str(cm.value) == (
            "The specified library was not found at path 'lib/charms/testcharm/v0/testlib.py'."
        )


def test_publishlib_not_from_current_charm(emitter, store_mock, tmp_path, monkeypatch, config):
    """The indicated library to publish does not belong to this charm."""
    monkeypatch.chdir(tmp_path)
    config.name = "charm2"
    factory.create_lib_filepath("testcharm", "testlib", api=0)

    args = Namespace(library="charms.testcharm.v0.testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "charm2"
        with pytest.raises(CraftError) as cm:
            PublishLibCommand(config).run(args)

        assert str(cm.value) == (
            "The library charms.testcharm.v0.testlib does not belong to this charm 'charm2'."
        )


@pytest.mark.xfail(
    strict=True,
    raises=pydantic.ValidationError,
    reason="Store commands need refactoring to not need a project.",
)
def test_publishlib_name_from_metadata_problem(store_mock, config):
    """The metadata wasn't there to get the name."""
    config.name = None
    args = Namespace(library="charms.testcharm.v0.testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = None
        with pytest.raises(CraftError) as cm:
            PublishLibCommand(config).run(args)

        assert str(cm.value) == (
            "Cannot find a valid charm name in charm definition. "
            "Check that you are using the correct project directory."
        )


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_store_is_advanced(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store has a higher revision number than what we expect."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("test-charm", "testlib", api=0, patch=1, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = (
        "Library charms.test_charm.v0.testlib is out-of-date locally, Charmhub has version 0.2, "
        "please fetch the updates before publishing."
    )
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages([error_message])


def test_publishlib_store_is_exactly_behind_ok(emitter, store_mock, tmp_path, monkeypatch, config):
    """The store is exactly one revision less than local lib, ok."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "test-charm", "testlib", api=0, patch=7, lib_id=lib_id
    )

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=6,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
        call.create_library_revision("test-charm", lib_id, 0, 7, content, content_hash),
    ]
    expected = "Library charms.test_charm.v0.testlib sent to the store with version 0.7"
    emitter.assert_message(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_store_is_exactly_behind_same_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store is exactly one revision less than local lib, same hash."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "test-charm", "testlib", api=0, patch=7, lib_id=lib_id
    )

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash=content_hash,
            api=0,
            patch=6,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = (
        "Library charms.test_charm.v0.testlib LIBPATCH number was incorrectly incremented, "
        "Charmhub has the same content in version 0.6."
    )
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages([error_message])


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_store_is_too_behind(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store is way more behind than what we expected (local lib too high!)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("test-charm", "testlib", api=0, patch=4, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = (
        "Library charms.test_charm.v0.testlib has a wrong LIBPATCH number, it's too high and needs "
        "to be consecutive, Charmhub highest version is 0.2."
    )
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages([error_message])


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_store_has_same_revision_same_hash(
    emitter,
    store_mock,
    tmp_path,
    monkeypatch,
    config,
    formatted,
):
    """The store has the same revision we want to publish, with the same hash."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "test-charm", "testlib", api=0, patch=7, lib_id=lib_id
    )

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash=content_hash,
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = "Library charms.test_charm.v0.testlib is already updated in Charmhub."
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages([error_message])


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_publishlib_store_has_same_revision_other_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store has the same revision we want to publish, but with a different hash."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("test-charm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    args = Namespace(library="charms.test_charm.v0.testlib", format=formatted)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "test-charm"
        PublishLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = (
        "Library charms.test_charm.v0.testlib version 0.7 is the same than in Charmhub but "
        "content is different"
    )
    if formatted:
        expected = [
            {
                "charm_name": "test-charm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages([error_message])


# -- tests for fetch libraries command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_simple_downloaded(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="testcharm",
    )

    args = Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "testcharm", "lib_name": "testlib", "api": 0}]),
        call.get_library("testcharm", lib_id, 0),
    ]
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "fetched": {
                    "patch": 7,
                    "content_hash": "abc",
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = "Library charms.testcharm.v0.testlib version 0.7 downloaded."
        emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "testcharm" / "v0" / "testlib.py"
    assert saved_file.read_text() == lib_content


def test_fetchlib_simple_dash_in_name(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="test-charm",
    )

    args = Namespace(library="charms.test_charm.v0.testlib", format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "test-charm", "lib_name": "testlib", "api": 0}]),
        call.get_library("test-charm", lib_id, 0),
    ]
    expected = "Library charms.test_charm.v0.testlib version 0.7 downloaded."
    emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "test_charm" / "v0" / "testlib.py"
    assert saved_file.read_text() == lib_content


def test_fetchlib_simple_dash_in_name_on_disk(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for the first time (downloading it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    lib_content = "test-content"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="test-charm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=lib_content,
        content_hash="abc",
        api=0,
        patch=7,
        lib_name="testlib",
        charm_name="test-charm",
    )
    factory.create_lib_filepath("test-charm", "testlib", api=0, patch=1, lib_id=lib_id)

    args = Namespace(library=None, format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": "test-example-lib-id", "api": 0}]),
        call.get_library("test-charm", lib_id, 0),
    ]
    expected = "Library charms.test_charm.v0.testlib updated to version 0.7."
    emitter.assert_message(expected)


def test_fetchlib_simple_updated(emitter, store_mock, tmp_path, monkeypatch, config):
    """Happy path fetching the lib for Nth time (updating it)."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    content, content_hash = factory.create_lib_filepath(
        "testcharm", "testlib", api=0, patch=1, lib_id=lib_id
    )

    new_lib_content = "some test content with uñicode ;)"
    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    store_mock.get_library.return_value = Library(
        lib_id=lib_id,
        content=new_lib_content,
        content_hash="abc",
        api=0,
        patch=2,
        lib_name="testlib",
        charm_name="testcharm",
    )

    args = Namespace(library="charms.testcharm.v0.testlib", format=None)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
        call.get_library("testcharm", lib_id, 0),
    ]
    expected = "Library charms.testcharm.v0.testlib updated to version 0.2."
    emitter.assert_message(expected)
    saved_file = tmp_path / "lib" / "charms" / "testcharm" / "v0" / "testlib.py"
    assert saved_file.read_text() == new_lib_content


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_all(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """Update all the libraries found in disk."""
    monkeypatch.chdir(tmp_path)

    c1, h1 = factory.create_lib_filepath(
        "testcharm1", "testlib1", api=0, patch=1, lib_id="lib_id_1"
    )
    c2, h2 = factory.create_lib_filepath(
        "testcharm2", "testlib2", api=3, patch=5, lib_id="lib_id_2"
    )

    store_mock.get_libraries_tips.return_value = {
        ("lib_id_1", 0): Library(
            lib_id="lib_id_1",
            content=None,
            content_hash="abc",
            api=0,
            patch=2,
            lib_name="testlib1",
            charm_name="testcharm1",
        ),
        ("lib_id_2", 3): Library(
            lib_id="lib_id_2",
            content=None,
            content_hash="def",
            api=3,
            patch=14,
            lib_name="testlib2",
            charm_name="testcharm2",
        ),
    }
    _store_libs_info = [
        Library(
            lib_id="lib_id_1",
            content="new lib content 1",
            content_hash="xxx",
            api=0,
            patch=2,
            lib_name="testlib1",
            charm_name="testcharm1",
        ),
        Library(
            lib_id="lib_id_2",
            content="new lib content 2",
            content_hash="yyy",
            api=3,
            patch=14,
            lib_name="testlib2",
            charm_name="testcharm2",
        ),
    ]
    store_mock.get_library.side_effect = lambda *a: _store_libs_info.pop(0)

    args = Namespace(library=None, format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips(
            [
                {"lib_id": "lib_id_1", "api": 0},
                {"lib_id": "lib_id_2", "api": 3},
            ]
        ),
        call.get_library("testcharm1", "lib_id_1", 0),
        call.get_library("testcharm2", "lib_id_2", 3),
    ]
    names = [
        "charms.testcharm1.v0.testlib1",
        "charms.testcharm2.v3.testlib2",
    ]
    emitter.assert_debug("Libraries found under 'lib/charms': " + str(names))
    if formatted:
        expected = [
            {
                "charm_name": "testcharm1",
                "library_name": "testlib1",
                "library_id": "lib_id_1",
                "api": 0,
                "fetched": {
                    "patch": 2,
                    "content_hash": "xxx",
                },
            },
            {
                "charm_name": "testcharm2",
                "library_name": "testlib2",
                "library_id": "lib_id_2",
                "api": 3,
                "fetched": {
                    "patch": 14,
                    "content_hash": "yyy",
                },
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(
            [
                "Library charms.testcharm1.v0.testlib1 updated to version 0.2.",
                "Library charms.testcharm2.v3.testlib2 updated to version 3.14.",
            ]
        )

    saved_file = tmp_path / "lib" / "charms" / "testcharm1" / "v0" / "testlib1.py"
    assert saved_file.read_text() == "new lib content 1"
    saved_file = tmp_path / "lib" / "charms" / "testcharm2" / "v3" / "testlib2.py"
    assert saved_file.read_text() == "new lib content 2"


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_not_found(emitter, store_mock, config, formatted):
    """The indicated library is not found in the store."""
    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "testcharm", "lib_name": "testlib", "api": 0}]),
    ]
    error_message = "Library charms.testcharm.v0.testlib not found in Charmhub."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": None,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_is_old(emitter, store_mock, tmp_path, monkeypatch, config, formatted):
    """The store has an older version that what is found locally."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=6,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = "Library charms.testcharm.v0.testlib has local changes, cannot be updated."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_same_versions_same_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store situation is the same than locally."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    _, c_hash = factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash=c_hash,
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = "Library charms.testcharm.v0.testlib was already up to date in version 0.7."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_fetchlib_store_same_versions_different_hash(
    emitter, store_mock, tmp_path, monkeypatch, config, formatted
):
    """The store has the lib in the same version, but with different content."""
    monkeypatch.chdir(tmp_path)

    lib_id = "test-example-lib-id"
    factory.create_lib_filepath("testcharm", "testlib", api=0, patch=7, lib_id=lib_id)

    store_mock.get_libraries_tips.return_value = {
        (lib_id, 0): Library(
            lib_id=lib_id,
            content=None,
            content_hash="abc",
            api=0,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = Namespace(library="charms.testcharm.v0.testlib", format=formatted)
    FetchLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"lib_id": lib_id, "api": 0}]),
    ]
    error_message = "Library charms.testcharm.v0.testlib has local changes, cannot be updated."
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": lib_id,
                "api": 0,
                "error_message": error_message,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        emitter.assert_message(error_message)


# -- tests for list libraries command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_listlib_simple(emitter, store_mock, config, formatted):
    """Happy path listing simple case."""
    store_mock.get_libraries_tips.return_value = {
        ("some-lib-id", 3): Library(
            lib_id="some-lib-id",
            content=None,
            content_hash="abc",
            api=3,
            patch=7,
            lib_name="testlib",
            charm_name="testcharm",
        ),
    }
    args = Namespace(name="testcharm", format=formatted)
    ListLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "testcharm"}]),
    ]
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib",
                "library_id": "some-lib-id",
                "api": 3,
                "patch": 7,
                "content_hash": "abc",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Library name    API    Patch",
            "testlib         3      7",
        ]
        emitter.assert_messages(expected)


def test_listlib_charm_from_metadata(emitter, store_mock, config):
    """Happy path listing simple case."""
    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(name=None, format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = "testcharm"
        ListLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "testcharm"}]),
    ]


def test_listlib_name_from_metadata_problem(store_mock, config):
    """The metadata wasn't there to get the name."""
    args = Namespace(name=None, format=None)
    with patch("charmcraft.utils.get_name_from_metadata") as mock:
        mock.return_value = None
        with pytest.raises(CraftError) as cm:
            ListLibCommand(config).run(args)

        assert str(cm.value) == (
            "Can't access name in 'metadata.yaml' file. The 'list-lib' command must either be "
            "executed from a valid project directory, or specify a charm name using "
            "the --charm-name option."
        )


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_listlib_empty(emitter, store_mock, config, formatted):
    """Nothing found in the store for the specified charm."""
    store_mock.get_libraries_tips.return_value = {}
    args = Namespace(name="testcharm", format=formatted)
    ListLibCommand(config).run(args)

    if formatted:
        emitter.assert_json_output([])
    else:
        expected = "No libraries found for charm testcharm."
        emitter.assert_message(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_listlib_properly_sorted(emitter, store_mock, config, formatted):
    """Check the sorting of the list."""
    store_mock.get_libraries_tips.return_value = {
        ("lib-id-2", 3): Library(
            lib_id="lib-id-2",
            content=None,
            content_hash="abc",
            api=3,
            patch=7,
            lib_name="testlib-2",
            charm_name="testcharm",
        ),
        ("lib-id-2", 2): Library(
            lib_id="lib-id-2",
            content=None,
            content_hash="abc",
            api=2,
            patch=8,
            lib_name="testlib-2",
            charm_name="testcharm",
        ),
        ("lib-id-1", 5): Library(
            lib_id="lib-id-1",
            content=None,
            content_hash="abc",
            api=5,
            patch=124,
            lib_name="testlib-1",
            charm_name="testcharm",
        ),
    }
    args = Namespace(name="testcharm", format=formatted)
    ListLibCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.get_libraries_tips([{"charm_name": "testcharm"}]),
    ]
    if formatted:
        expected = [
            {
                "charm_name": "testcharm",
                "library_name": "testlib-1",
                "library_id": "lib-id-1",
                "api": 5,
                "patch": 124,
                "content_hash": "abc",
            },
            {
                "charm_name": "testcharm",
                "library_name": "testlib-2",
                "library_id": "lib-id-2",
                "api": 2,
                "patch": 8,
                "content_hash": "abc",
            },
            {
                "charm_name": "testcharm",
                "library_name": "testlib-2",
                "library_id": "lib-id-2",
                "api": 3,
                "patch": 7,
                "content_hash": "abc",
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Library name    API    Patch",
            "testlib-1       5      124",
            "testlib-2       2      8",
            "testlib-2       3      7",
        ]
        emitter.assert_messages(expected)


# -- tests for list resources command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resources_simple(emitter, store_mock, config, formatted):
    """Happy path of one result from the Store."""
    store_response = [
        Resource(name="testresource", optional=True, revision=1, resource_type="file"),
    ]
    store_mock.list_resources.return_value = store_response

    args = Namespace(charm_name="testcharm", format=formatted)
    ListResourcesCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_resources("testcharm"),
    ]
    if formatted:
        expected = [
            {
                "charm_revision": 1,
                "name": "testresource",
                "type": "file",
                "optional": True,
            }
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Charm Rev    Resource      Type    Optional",
            "1            testresource  file    True",
        ]
        emitter.assert_messages(expected)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resources_empty(emitter, store_mock, config, formatted):
    """No results from the store."""
    store_response = []
    store_mock.list_resources.return_value = store_response

    args = Namespace(charm_name="testcharm", format=formatted)
    ListResourcesCommand(config).run(args)

    if formatted:
        emitter.assert_json_output([])
    else:
        emitter.assert_message("No resources associated to testcharm.")


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resources_ordered_and_grouped(emitter, store_mock, config, formatted):
    """Results are presented ordered by name in the table."""
    store_response = [
        Resource(name="bbb-resource", optional=True, revision=2, resource_type="file"),
        Resource(name="ccc-resource", optional=True, revision=1, resource_type="file"),
        Resource(name="bbb-resource", optional=False, revision=3, resource_type="file"),
        Resource(name="aaa-resource", optional=True, revision=2, resource_type="oci-image"),
        Resource(name="bbb-resource", optional=True, revision=5, resource_type="file"),
    ]
    store_mock.list_resources.return_value = store_response

    args = Namespace(charm_name="testcharm", format=formatted)
    ListResourcesCommand(config).run(args)

    if formatted:
        expected = [
            {
                "charm_revision": 2,
                "name": "bbb-resource",
                "type": "file",
                "optional": True,
            },
            {
                "charm_revision": 1,
                "name": "ccc-resource",
                "type": "file",
                "optional": True,
            },
            {
                "charm_revision": 3,
                "name": "bbb-resource",
                "type": "file",
                "optional": False,
            },
            {
                "charm_revision": 2,
                "name": "aaa-resource",
                "type": "oci-image",
                "optional": True,
            },
            {
                "charm_revision": 5,
                "name": "bbb-resource",
                "type": "file",
                "optional": True,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Charm Rev    Resource      Type       Optional",
            "5            bbb-resource  file       True",
            "3            bbb-resource  file       False",
            "2            aaa-resource  oci-image  True",
            "             bbb-resource  file       True",
            "1            ccc-resource  file       True",
        ]
        emitter.assert_messages(expected)


# -- tests for upload resources command


def test_uploadresource_options_filepath_type(config):
    """The --filepath option implies a set of validations."""
    cmd = UploadResourceCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "filepath")
    assert isinstance(action.type, SingleOptionEnsurer)
    assert action.type.converter is useful_filepath


def test_uploadresource_options_image_type(config):
    """The --image option implies a set of validations."""
    cmd = UploadResourceCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    (action,) = (action for action in parser._actions if action.dest == "image")
    assert isinstance(action.type, SingleOptionEnsurer)
    assert action.type.converter is str


@pytest.mark.parametrize(
    "sysargs",
    [
        ("c", "r", "--filepath=fpath"),
        ("c", "r", "--image=x"),
    ],
)
def test_uploadresource_options_good_combinations(tmp_path, config, sysargs, monkeypatch):
    """Check the specific rules for filepath and image/[registry] good combinations."""
    # fake the file for filepath
    (tmp_path / "fpath").touch()
    monkeypatch.chdir(tmp_path)

    cmd = UploadResourceCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    try:
        parser.parse_args(sysargs)
    except SystemExit:
        pytest.fail("Argument parsing expected to succeed but failed")


@pytest.mark.parametrize(
    "sysargs",
    [
        ("c", "r"),  # filepath XOR image needs to be specified
        ("c", "r", "--filepath=fpath", "--image=y"),  # can't specify both
    ],
)
def test_uploadresource_options_bad_combinations(config, sysargs, tmp_path, monkeypatch):
    """Check the specific rules for filepath and image/[registry] bad combinations."""
    # fake the file for filepath
    (tmp_path / "fpath").touch()
    monkeypatch.chdir(tmp_path)

    cmd = UploadResourceCommand(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    with pytest.raises(SystemExit):
        parsed_args = parser.parse_args(sysargs)
        cmd.parsed_args_post_verification(parser, parsed_args)


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_uploadresource_filepath_call_ok(emitter, store_mock, config, tmp_path, formatted):
    """Simple upload, success result."""
    store_response = Uploaded(ok=True, status=200, revision=7, errors=[])
    store_mock.upload_resource.return_value = store_response

    test_resource = tmp_path / "mystuff.bin"
    test_resource.write_text("sample stuff")
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=test_resource,
        image=None,
        format=formatted,
    )
    retcode = UploadResourceCommand(config).run(args)
    assert retcode == 0

    assert store_mock.mock_calls == [
        call.upload_resource("mycharm", "myresource", "file", test_resource)
    ]
    if formatted:
        expected = {"revision": 7}
        emitter.assert_json_output(expected)
    else:
        emitter.assert_interactions(
            [
                call("progress", f"Uploading resource directly from file {str(test_resource)!r}."),
                call(
                    "message", "Revision 7 created of resource 'myresource' for charm 'mycharm'."
                ),
            ]
        )
    assert test_resource.exists()  # provided by the user, don't touch it


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_uploadresource_image_digest_already_uploaded(emitter, store_mock, config, formatted):
    """Upload an oci-image resource, the image itself already being in the registry."""
    # fake credentials for the charm/resource, and the final json content
    store_mock.get_oci_registry_credentials.return_value = RegistryCredentials(
        username="testusername",
        password="testpassword",
        image_name="registry.staging.jujucharms.com/charm/charm-id/test-image-name",
    )

    test_json_content = "from charmhub we came, to charmhub we shall return"
    store_mock.get_oci_image_blob.return_value = test_json_content

    # hack into the store mock to save for later the uploaded resource bytes
    uploaded_resource_content = None
    uploaded_resource_filepath = None

    def interceptor(charm_name, resource_name, resource_type, resource_filepath):
        """Intercept the call to save real content (and validate params)."""
        nonlocal uploaded_resource_content, uploaded_resource_filepath

        uploaded_resource_filepath = resource_filepath
        uploaded_resource_content = resource_filepath.read_text()

        assert charm_name == "mycharm"
        assert resource_name == "myresource"
        assert resource_type == "oci-image"
        return Uploaded(ok=True, status=200, revision=7, errors=[])

    store_mock.upload_resource.side_effect = interceptor

    # test
    original_image_digest = "sha256:test-digest-given-by-user"
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=None,
        image=original_image_digest,
        format=formatted,
    )
    with patch("charmcraft.commands.store.ImageHandler", autospec=True) as im_class_mock:
        with patch("charmcraft.commands.store.OCIRegistry", autospec=True) as reg_class_mock:
            reg_class_mock.return_value = reg_mock = MagicMock()
            im_class_mock.return_value = im_mock = MagicMock()
            im_mock.check_in_registry.return_value = True
            UploadResourceCommand(config).run(args)

    # validate how OCIRegistry was instantiated
    assert reg_class_mock.mock_calls == [
        call(
            config.charmhub.registry_url,
            "charm/charm-id/test-image-name",
            username="testusername",
            password="testpassword",
        )
    ]

    # validate how ImageHandler was used
    assert im_class_mock.mock_calls == [
        call(reg_mock),
        call().check_in_registry(original_image_digest),
    ]

    # check that the uploaded file is fine and that was cleaned
    assert uploaded_resource_content == test_json_content
    assert not uploaded_resource_filepath.exists()  # temporary! shall be cleaned

    assert store_mock.mock_calls == [
        call.get_oci_registry_credentials("mycharm", "myresource"),
        call.get_oci_image_blob("mycharm", "myresource", original_image_digest),
        call.upload_resource("mycharm", "myresource", "oci-image", uploaded_resource_filepath),
    ]

    if formatted:
        expected = {"revision": 7}
        emitter.assert_json_output(expected)
    else:
        emitter.assert_interactions(
            [
                call(
                    "progress",
                    "Uploading resource from image "
                    "charm/charm-id/test-image-name @ sha256:test-digest-given-by-user.",
                ),
                call("progress", "Using OCI image from Canonical's registry.", permanent=True),
                call(
                    "message", "Revision 7 created of resource 'myresource' for charm 'mycharm'."
                ),
            ]
        )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_uploadresource_image_digest_upload_from_local(emitter, store_mock, config):
    """Upload an oci-image resource, from local to Canonical's registry, specified by digest."""
    # fake credentials for the charm/resource, the final json content, and the upload result
    store_mock.get_oci_registry_credentials.return_value = RegistryCredentials(
        username="testusername",
        password="testpassword",
        image_name="registry.staging.jujucharms.com/charm/charm-id/test-image-name",
    )

    test_json_content = "from charmhub we came, to charmhub we shall return"
    store_mock.get_oci_image_blob.return_value = test_json_content

    store_mock.upload_resource.return_value = Uploaded(ok=True, status=200, revision=7, errors=[])

    # test
    original_image_digest = "sha256:test-digest-given-by-user"
    local_image_info = "local image info"
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=None,
        image=original_image_digest,
        format=False,
    )
    with patch("charmcraft.commands.store.ImageHandler", autospec=True) as im_class_mock:
        with patch(
            "charmcraft.commands.store.LocalDockerdInterface", autospec=True
        ) as dockerd_class_mock:
            im_class_mock.return_value = im_mock = MagicMock()
            dockerd_class_mock.return_value = dock_mock = MagicMock()

            # not in the remote registry, found locally, then uploaded ok
            im_mock.check_in_registry.return_value = False
            dock_mock.get_image_info_from_digest.return_value = local_image_info
            new_image_digest = "new-digest-after-upload"
            im_mock.upload_from_local.return_value = new_image_digest

            UploadResourceCommand(config).run(args)

    # validate how ImageHandler was used
    assert im_mock.mock_calls == [
        call.check_in_registry(original_image_digest),
        call.upload_from_local(local_image_info),
    ]

    assert store_mock.mock_calls == [
        call.get_oci_registry_credentials("mycharm", "myresource"),
        call.get_oci_image_blob("mycharm", "myresource", new_image_digest),
        call.upload_resource("mycharm", "myresource", "oci-image", ANY),
    ]

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Uploading resource from image "
                "charm/charm-id/test-image-name @ sha256:test-digest-given-by-user.",
            ),
            call("progress", "Remote image not found, getting its info from local registry."),
            call("progress", "Uploading from local registry.", permanent=True),
            call(
                "progress",
                "Image uploaded, new remote digest: new-digest-after-upload.",
                permanent=True,
            ),
            call("message", "Revision 7 created of resource 'myresource' for charm 'mycharm'."),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_uploadresource_image_id_upload_from_local(emitter, store_mock, config):
    """Upload an oci-image resource, from local to Canonical's registry, specified by id."""
    # fake credentials for the charm/resource, the final json content, and the upload result
    store_mock.get_oci_registry_credentials.return_value = RegistryCredentials(
        username="testusername",
        password="testpassword",
        image_name="registry.staging.jujucharms.com/charm/charm-id/test-image-name",
    )

    test_json_content = "from charmhub we came, to charmhub we shall return"
    store_mock.get_oci_image_blob.return_value = test_json_content

    store_mock.upload_resource.return_value = Uploaded(ok=True, status=200, revision=7, errors=[])

    # test
    original_image_id = "test-id-given-by-user"
    local_image_info = "local image info"
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=None,
        image=original_image_id,
        format=False,
    )
    with patch("charmcraft.commands.store.ImageHandler", autospec=True) as im_class_mock:
        with patch(
            "charmcraft.commands.store.LocalDockerdInterface", autospec=True
        ) as dockerd_class_mock:
            im_class_mock.return_value = im_mock = MagicMock()
            dockerd_class_mock.return_value = dock_mock = MagicMock()

            # found locally, then uploaded ok
            dock_mock.get_image_info_from_id.return_value = local_image_info
            new_image_digest = "new-digest-after-upload"
            im_mock.upload_from_local.return_value = new_image_digest

            UploadResourceCommand(config).run(args)

    # validate how ImageHandler was used
    assert im_mock.mock_calls == [
        call.upload_from_local(local_image_info),
    ]

    assert store_mock.mock_calls == [
        call.get_oci_registry_credentials("mycharm", "myresource"),
        call.get_oci_image_blob("mycharm", "myresource", new_image_digest),
        call.upload_resource("mycharm", "myresource", "oci-image", ANY),
    ]

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Uploading resource from image "
                "charm/charm-id/test-image-name @ test-id-given-by-user.",
            ),
            call("progress", "Getting image info from local registry."),
            call("progress", "Uploading from local registry.", permanent=True),
            call(
                "progress",
                "Image uploaded, new remote digest: new-digest-after-upload.",
                permanent=True,
            ),
            call("message", "Revision 7 created of resource 'myresource' for charm 'mycharm'."),
        ]
    )


def test_uploadresource_image_digest_missing_everywhere(emitter, store_mock, config):
    """Upload an oci-image resource by digest, but the image is not found remote nor locally."""
    # fake credentials for the charm/resource, the final json content, and the upload result
    store_mock.get_oci_registry_credentials.return_value = RegistryCredentials(
        username="testusername",
        password="testpassword",
        image_name="registry.staging.jujucharms.com/charm/charm-id/test-image-name",
    )

    # test
    original_image_digest = "sha256:test-digest-given-by-user"
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=None,
        image=original_image_digest,
        format=False,
    )
    with patch("charmcraft.commands.store.ImageHandler", autospec=True) as im_class_mock:
        with patch(
            "charmcraft.commands.store.LocalDockerdInterface", autospec=True
        ) as dockerd_class_mock:
            im_class_mock.return_value = im_mock = MagicMock()
            dockerd_class_mock.return_value = dock_mock = MagicMock()

            # not in the remote registry, not locally either
            im_mock.check_in_registry.return_value = False
            dock_mock.get_image_info_from_digest.return_value = None

            with pytest.raises(CraftError) as cm:
                UploadResourceCommand(config).run(args)

    assert str(cm.value) == "Image not found locally."

    # validate how local interfaces and store was used
    assert im_mock.mock_calls == [
        call.check_in_registry(original_image_digest),
    ]
    assert dock_mock.mock_calls == [
        call.get_image_info_from_digest(original_image_digest),
    ]
    assert store_mock.mock_calls == [
        call.get_oci_registry_credentials("mycharm", "myresource"),
    ]

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Uploading resource from "
                "image charm/charm-id/test-image-name @ sha256:test-digest-given-by-user.",
            ),
            call("progress", "Remote image not found, getting its info from local registry."),
        ]
    )


def test_uploadresource_image_id_missing(emitter, store_mock, config):
    """Upload an oci-image resource by id, but the image is not found locally."""
    # fake credentials for the charm/resource, the final json content, and the upload result
    store_mock.get_oci_registry_credentials.return_value = RegistryCredentials(
        username="testusername",
        password="testpassword",
        image_name="registry.staging.jujucharms.com/charm/charm-id/test-image-name",
    )

    # test
    original_image_id = "test-id-given-by-user"
    args = Namespace(
        charm_name="mycharm",
        resource_name="myresource",
        filepath=None,
        image=original_image_id,
        format=False,
    )
    with patch(
        "charmcraft.commands.store.LocalDockerdInterface", autospec=True
    ) as dockerd_class_mock:
        dockerd_class_mock.return_value = dock_mock = MagicMock()

        # not present locally
        dock_mock.get_image_info_from_id.return_value = None

        with pytest.raises(CraftError) as cm:
            UploadResourceCommand(config).run(args)

    assert str(cm.value) == "Image not found locally."

    assert dock_mock.mock_calls == [
        call.get_image_info_from_id(original_image_id),
    ]
    assert store_mock.mock_calls == [
        call.get_oci_registry_credentials("mycharm", "myresource"),
    ]

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Uploading resource from "
                "image charm/charm-id/test-image-name @ test-id-given-by-user.",
            ),
            call("progress", "Getting image info from local registry."),
        ]
    )


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_uploadresource_call_error(emitter, store_mock, config, tmp_path, formatted):
    """Simple upload but with a response indicating an error."""
    errors = [
        Error(message="text 1", code="missing-stuff"),
        Error(message="other long error text", code="broken"),
    ]
    store_response = Uploaded(ok=False, status=400, revision=None, errors=errors)
    store_mock.upload_resource.return_value = store_response

    test_resource = tmp_path / "mystuff.bin"
    test_resource.write_text("sample stuff")
    args = Namespace(
        charm_name="mycharm", resource_name="myresource", filepath=test_resource, format=formatted
    )
    retcode = UploadResourceCommand(config).run(args)
    assert retcode == 1

    if formatted:
        expected = {
            "errors": [
                {"code": "missing-stuff", "message": "text 1"},
                {"code": "broken", "message": "other long error text"},
            ]
        }
        emitter.assert_json_output(expected)
    else:
        emitter.assert_messages(
            [
                "Upload failed with status 400:",
                "- missing-stuff: text 1",
                "- broken: other long error text",
            ]
        )


# -- tests for list resource revisions command


@pytest.mark.parametrize("formatted", [None, JSON_FORMAT])
def test_resourcerevisions_simple(emitter, store_mock, config, formatted):
    """Happy path of one result from the Store."""
    store_response = [
        ResourceRevision(revision=1, size=50, created_at=datetime.datetime(2020, 7, 3, 2, 30, 40)),
    ]
    store_mock.list_resource_revisions.return_value = store_response

    args = Namespace(charm_name="testcharm", resource_name="testresource", format=formatted)
    ListResourceRevisionsCommand(config).run(args)

    assert store_mock.mock_calls == [
        call.list_resource_revisions("testcharm", "testresource"),
    ]
    if formatted:
        expected = [
            {
                "revision": 1,
                "created at": "2020-07-03T02:30:40Z",
                "size": 50,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Created at              Size",
            "1           2020-07-03T02:30:40Z     50B",
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
    tstamp = datetime.datetime(2020, 7, 3, 20, 30, 40)
    store_response = [
        ResourceRevision(revision=1, size=5000, created_at=tstamp),
        ResourceRevision(revision=3, size=34450520, created_at=tstamp),
        ResourceRevision(revision=4, size=876543, created_at=tstamp),
        ResourceRevision(revision=2, size=50, created_at=tstamp),
    ]
    store_mock.list_resource_revisions.return_value = store_response

    args = Namespace(charm_name="testcharm", resource_name="testresource", format=formatted)
    ListResourceRevisionsCommand(config).run(args)

    if formatted:
        expected = [
            {
                "revision": 1,
                "created at": "2020-07-03T20:30:40Z",
                "size": 5000,
            },
            {
                "revision": 3,
                "created at": "2020-07-03T20:30:40Z",
                "size": 34450520,
            },
            {
                "revision": 4,
                "created at": "2020-07-03T20:30:40Z",
                "size": 876543,
            },
            {
                "revision": 2,
                "created at": "2020-07-03T20:30:40Z",
                "size": 50,
            },
        ]
        emitter.assert_json_output(expected)
    else:
        expected = [
            "Revision    Created at              Size",
            "4           2020-07-03T20:30:40Z  856.0K",
            "3           2020-07-03T20:30:40Z   32.9M",
            "2           2020-07-03T20:30:40Z     50B",
            "1           2020-07-03T20:30:40Z    4.9K",
        ]
        emitter.assert_messages(expected)
