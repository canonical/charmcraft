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

import argparse
import ast
import datetime
import itertools
import os
import subprocess
import sys
from argparse import ArgumentParser
from textwrap import dedent
from unittest.mock import patch

import pytest
from craft_cli import (
    CraftError,
)
from craft_store.errors import CraftStoreError

from charmcraft import const, models, utils
from charmcraft.bases import get_host_as_base
from charmcraft.cmdbase import FORMAT_HELP_STR, JSON_FORMAT, BaseCommand
from charmcraft.main import COMMAND_GROUPS, _get_system_details, main
from charmcraft.models.charmcraft import BasesConfiguration

# --- Tests for the main entry point

# In all the test methods below we patch Dispatcher.run so we don't really exercise any
# command machinery, even if we call to main using a real command (which is to just
# make argument parsing system happy).


@pytest.fixture()
def config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(models.charmcraft.CharmcraftConfig, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                if self.parts is None:
                    self.parts = {}
                self.parts["charm"] = {"plugin": "charm", "prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = models.charmcraft.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    base = BasesConfiguration(**{"build-on": [get_host_as_base()], "run-on": [get_host_as_base()]})

    return TestConfig(
        type="charm",
        bases=[base],
        project=project,
        name="test-charm",
        summary="test summary",
        description="test description",
    )


def test_main_managed_instance_init(monkeypatch):
    """Init emitter with a specific log filepath."""
    monkeypatch.setenv(const.MANAGED_MODE_ENV_VAR, "1")

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            main(["charmcraft", "version"])

    # Emitter is init'd by craft-application
    emit_mock.init.assert_not_called()


@pytest.mark.parametrize(
    "side_effect",
    [
        ValueError("broken"),
        KeyboardInterrupt("interrupted"),
        CraftStoreError("bad server"),
        CraftError("bad charmcraft"),
    ],
)
def test_main_managed_instance_error(monkeypatch, side_effect, config):
    """The managed instance will not expose the "internal" log filepath."""
    monkeypatch.setenv(const.MANAGED_MODE_ENV_VAR, "1")

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.pre_parse_args") as d_mock:
            d_mock.side_effect = side_effect
            main(["charmcraft", "version"])

    # check that the error sent to Craft CLI will not report the logpath
    (end_in_error_call,) = emit_mock.error.mock_calls
    error = end_in_error_call.args[0]
    assert error.logpath_report is False


def test_main_no_args():
    """The setup.py entry_point function needs to work with no arguments."""
    with patch("sys.argv", ["charmcraft"]):
        retcode = main(sys.argv)

    assert retcode == 1


# -- tests for system details producer


def test_systemdetails_basic():
    """Basic system details."""
    with patch("os.environ", {}):
        with patch("charmcraft.utils.get_os_platform") as platform_mock:
            platform_mock.return_value = utils.OSPlatform(
                system="test-system", release="test-release", machine="test-machine"
            )
            result = _get_system_details()
    assert result == (
        "System details: OSPlatform(system='test-system', release='test-release', "
        "machine='test-machine'); Environment: None"
    )


def test_systemdetails_extra_environment(monkeypatch):
    """System details with extra environment variables."""
    with patch("os.environ", {"TEST1": "test1", "TEST2": "test2", "TEST3": "test3"}):
        with patch("charmcraft.utils.get_os_platform") as platform_mock:
            platform_mock.return_value = utils.OSPlatform(
                system="test-system", release="test-release", machine="test-machine"
            )
            with patch("charmcraft.main.EXTRA_ENVIRONMENT", ("TEST1", "TEST3")):
                result = _get_system_details()
    assert result == (
        "System details: OSPlatform(system='test-system', release='test-release', "
        "machine='test-machine'); Environment: TEST1='test1', TEST3='test3'"
    )


def test_systemdetails_charmcraft_environment():
    """System details with environment variables specific to Charmcraft."""
    with patch("os.environ", {"CHARMCRAFT-TEST": "testvalue"}):
        with patch("charmcraft.utils.get_os_platform") as platform_mock:
            platform_mock.return_value = utils.OSPlatform(
                system="test-system", release="test-release", machine="test-machine"
            )
            result = _get_system_details()
    assert result == (
        "System details: OSPlatform(system='test-system', release='test-release', "
        "machine='test-machine'); Environment: CHARMCRAFT-TEST='testvalue'"
    )


def test_systemdetails_hidden_auth():
    """System details specifically hiding secrets."""
    with patch("os.environ", {const.ALTERNATE_AUTH_ENV_VAR: "supersecret"}):
        with patch("charmcraft.utils.get_os_platform") as platform_mock:
            platform_mock.return_value = utils.OSPlatform(
                system="test-system", release="test-release", machine="test-machine"
            )
            result = _get_system_details()
    assert result == (
        "System details: OSPlatform(system='test-system', release='test-release', "
        f"machine='test-machine'); Environment: {const.ALTERNATE_AUTH_ENV_VAR}='<hidden>'"
    )


# -- generic tests for all Charmcraft commands

all_commands = list(itertools.chain(*(cgroup.commands for cgroup in COMMAND_GROUPS)))


@pytest.mark.parametrize("command", all_commands)
def test_legacy_commands(command):
    """Assert commands are valid.

    This is done through asking help for it *in real life*, which would mean that the
    command is usable by the tool: that can be imported, instantiated, parse arguments, etc.
    """
    env = os.environ.copy()

    # Bypass unsupported environment error.
    env[const.DEVELOPER_MODE_ENV_VAR] = "1"

    env_paths = [p for p in sys.path if "env/lib/python" in p]
    if env_paths:
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] += ":" + ":".join(env_paths)
        else:
            env["PYTHONPATH"] = ":".join(env_paths)

    external_command = [sys.executable, "-m", "charmcraft.main", command.name, "-h"]
    subprocess.run(external_command, check=True, env=env, stdout=subprocess.DEVNULL)


@pytest.mark.parametrize("command", all_commands)
def test_aesthetic_help_msg(command):
    """All real commands help msgs start with uppercase and do not end with a dot."""
    msg = command.help_msg
    assert msg[0].isupper()
    assert msg[-1] != "."


@pytest.mark.parametrize("command", all_commands)
def test_aesthetic_args_options_msg(command, config):
    """All real commands args help messages start with uppercase and do not end with a dot."""

    class FakeParser:
        """A fake to get the arguments added."""

        def add_mutually_exclusive_group(self, *args, **kwargs):
            """Return self, as it is used to add arguments too."""
            return self

        def add_argument(self, *args, **kwargs):
            """Verify that all commands have a correctly formatted help."""
            help_msg = kwargs.get("help")
            assert help_msg, "The help message must be present in each option"
            assert help_msg[0].isupper()
            assert help_msg[-1] != "."

    command(config).fill_parser(FakeParser())


@pytest.mark.parametrize("command_class", all_commands)
def test_usage_of_parsed_args(command_class, config):
    """The elements accessed on parsed_args need to be added before.

    This test is useful because normally all the tests for any command fake the
    Namespace and it happened in the past that we added functionality in the command
    execution but forgot to add the parameter in the 'fill_parser' method.
    """
    # get the list of attributes added by the command to the parser
    cmd = command_class(config)
    parser = ArgumentParser()
    cmd.fill_parser(parser)
    added_attributes = {action.dest for action in parser._actions}

    # build the abstract source tree for the command
    filepath = sys.modules[command_class.__module__].__file__
    tree = ast.parse(open(filepath).read())

    # get the node for the command
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == command_class.__name__:
            class_node = node
            break
    else:
        pytest.fail(f"Cannot find the class node for command {command_class}")

    # get the node for the 'run' function
    for node in ast.walk(class_node):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            run_method_node = node
            break
    else:
        pytest.fail(f"Cannot find the 'run' method node for command {command_class}")

    # get how the second argument to the function is called (normally
    # "parsed_args", but it's not enforced by the system)
    arg1, arg2 = run_method_node.args.args
    assert arg1.arg == "self"
    parsed_args_arg = arg2.arg

    for node in ast.walk(run_method_node):
        if not isinstance(node, ast.Attribute):
            continue
        attrib_value = node.value

        if isinstance(attrib_value, ast.Name) and attrib_value.id == parsed_args_arg:
            accessed_attribute = node.attr
            if accessed_attribute not in added_attributes:
                pytest.fail(
                    f"Found an accessed but not added argument ({accessed_attribute!r}) "
                    f"in command {command_class}"
                )


# -- tests for the base command


class MySimpleCommand(BaseCommand):
    """A simple minimal command to be used by different tests."""

    help_msg = "some help"
    name = "cmdname"
    overview = "test overview"


def test_basecommand_include_format_option(config):
    """Include a format option in the received parser."""
    parser = argparse.ArgumentParser()
    cmd = MySimpleCommand(config)
    cmd.include_format_option(parser)

    (action,) = (action for action in parser._actions if action.dest == "format")
    assert action.option_strings == ["--format"]
    assert action.dest == "format"
    assert action.default is None
    assert action.choices == [JSON_FORMAT]
    assert action.help == FORMAT_HELP_STR


def test_basecommand_format_content_json(config):
    """Properly format content in JSON format."""
    data = ["foo", "bar"]
    cmd = MySimpleCommand(config)
    result = cmd.format_content(JSON_FORMAT, data)
    assert result == dedent(
        """\
        [
            "foo",
            "bar"
        ]"""
    )


def test_basecommand_format_content_unkown(config):
    """The specified format is unknown."""
    cmd = MySimpleCommand(config)
    with pytest.raises(ValueError):
        cmd.format_content("bad format", {})
