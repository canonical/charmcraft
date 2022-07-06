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
import os
import subprocess
import sys
import textwrap
from argparse import ArgumentParser
from unittest.mock import patch

import pytest
from craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    CraftError,
    EmitterMode,
    ProvideHelpException,
)
from craft_store.errors import CraftStoreError

from charmcraft import __version__, env, utils
from charmcraft.cmdbase import BaseCommand, JSON_FORMAT
from charmcraft.commands.store.client import ALTERNATE_AUTH_ENV_VAR
from charmcraft.main import COMMAND_GROUPS, main, _get_system_details


@pytest.fixture
def base_config_present(create_config, monkeypatch):
    tmp_path = create_config(
        """
        type: charm
        bases:
          - name: ubuntu
            channel: "20.04"
    """
    )
    monkeypatch.chdir(tmp_path)


# --- Tests for the main entry point

# In all the test methods below we patch Dispatcher.run so we don't really exercise any
# command machinery, even if we call to main using a real command (which is to just
# make argument parsing system happy).


def test_main_ok():
    """Work ended ok: message handler notified properly, return code in 0."""
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            retcode = main(["charmcraft", "version"])

    assert retcode == 0
    emit_mock.ended_ok.assert_called_once_with()

    # check how Emitter was initted
    emit_mock.init.assert_called_once_with(
        EmitterMode.BRIEF,
        "charmcraft",
        f"Starting charmcraft version {__version__}",
        log_filepath=None,
    )


def test_main_managed_instance_init(monkeypatch):
    """Init emitter with a specific log filepath."""
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            main(["charmcraft", "version"])

    # check how Emitter was initted
    emit_mock.init.assert_called_once_with(
        EmitterMode.BRIEF,
        "charmcraft",
        f"Starting charmcraft version {__version__}",
        log_filepath=env.get_managed_environment_log_path(),
    )


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
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.pre_parse_args") as d_mock:
            d_mock.side_effect = side_effect
            main(["charmcraft", "version"])

    # check that the error sent to Craft CLI will not report the logpath
    (end_in_error_call,) = emit_mock.error.mock_calls
    error = end_in_error_call.args[0]
    assert error.logpath_report is False


def test_main_load_config_ok(create_config):
    """Command is properly executed, after loading and receiving the config."""
    tmp_path = create_config(
        """
        type: bundle
    """
    )

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"
        overview = "test overview"

        def run(self, parsed_args):
            assert self.config.type == "bundle"

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", f"--project-dir={tmp_path}"])
    assert retcode == 0


def test_main_load_config_not_present_ok():
    """Config is not present but the command does not need it."""

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"
        overview = "test overview"

        def run(self, parsed_args):
            assert not self.config.project.config_provided

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", "--project-dir=/whatever"])
    assert retcode == 0


def test_main_load_config_not_present_but_needed(capsys):
    """Config is not present and the command needs it."""

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"
        overview = "test overview"
        needs_config = True

        def run(self, parsed_args):
            pass

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", "--project-dir=/whatever"])
    assert retcode == 1

    out, err = capsys.readouterr()
    assert not out
    assert err == (
        "The specified command needs a valid 'charmcraft.yaml' configuration file (in "
        "the current directory or where specified with --project-dir option); see "
        "the reference: https://discourse.charmhub.io/t/charmcraft-configuration/4138\n"
    )


def test_main_no_args():
    """The setup.py entry_point function needs to work with no arguments."""
    with patch("sys.argv", ["charmcraft"]):
        retcode = main()

    assert retcode == 1


def test_main_controlled_error(base_config_present):
    """Work raised CraftError: message handler notified properly, use indicated return code."""
    simulated_exception = CraftError("boom", retcode=33)
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 33
    emit_mock.error.assert_called_once_with(simulated_exception)


def test_main_controlled_return_code(base_config_present):
    """Work ended ok, and the command indicated the return code."""
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = 9
            retcode = main(["charmcraft", "version"])

    assert retcode == 9
    emit_mock.ended_ok.assert_called_once_with()


def test_main_crash(base_config_present):
    """Work crashed: message handler notified properly, return code in 1."""
    simulated_exception = ValueError("boom")
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    (call,) = emit_mock.error.mock_calls
    (exc,) = call.args
    assert isinstance(exc, CraftError)
    assert str(exc) == "charmcraft internal error: ValueError('boom')"
    assert exc.__cause__ == simulated_exception


def test_main_interrupted(base_config_present):
    """Work interrupted: message handler notified properly, return code in 1."""
    simulated_exception = KeyboardInterrupt()
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    (call,) = emit_mock.error.mock_calls
    (exc,) = call.args
    assert isinstance(exc, CraftError)
    assert str(exc) == "Interrupted."
    assert exc.__cause__ == simulated_exception


def test_main_controlled_arguments_error(capsys, base_config_present):
    """The execution failed because an argument parsing error."""
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = ArgumentParsingError("test error")
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    emit_mock.ended_ok.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert err == "test error\n"


def test_main_providing_help(capsys, base_config_present):
    """The execution ended up providing a help message."""
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = ProvideHelpException("nice and shiny help message")
            retcode = main(["charmcraft", "version"])

    assert retcode == 0
    emit_mock.ended_ok.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert err == "nice and shiny help message\n"


def test_main_logs_system_details(emitter, config):
    """Calling main ends up logging the system details."""
    system_details = "test system details"

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as run_mock:
            with patch("charmcraft.main._get_system_details") as details_mock:
                details_mock.return_value = system_details
                run_mock.return_value = None
                main(["charmcraft", "version"])
    emit_mock.debug.assert_called_once_with(system_details)


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


def test_systemdetails_no_auth():
    """System details specifically excluding secrets."""
    with patch("os.environ", {ALTERNATE_AUTH_ENV_VAR: "supersecret"}):
        with patch("charmcraft.utils.get_os_platform") as platform_mock:
            platform_mock.return_value = utils.OSPlatform(
                system="test-system", release="test-release", machine="test-machine"
            )
            result = _get_system_details()
    assert result == (
        "System details: OSPlatform(system='test-system', release='test-release', "
        "machine='test-machine'); Environment: None"
    )


# -- generic tests for all Charmcraft commands

all_commands = list.__add__(*[cgroup.commands for cgroup in COMMAND_GROUPS])


@pytest.mark.parametrize("command", all_commands)
def test_commands(command):
    """Assert commands are valid.

    This is done through asking help for it *in real life*, which would mean that the
    command is usable by the tool: that can be imported, instantiated, parse arguments, etc.
    """
    env = os.environ.copy()

    # Bypass unsupported environment error.
    env["CHARMCRAFT_DEVELOPER"] = "1"

    env_paths = [p for p in sys.path if "env/lib/python" in p]
    if env_paths:
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] += ":" + ":".join(env_paths)
        else:
            env["PYTHONPATH"] = ":".join(env_paths)

    external_command = [sys.executable, "-m", "charmcraft", command.name, "-h"]
    subprocess.run(external_command, check=True, env=env, stdout=subprocess.DEVNULL)


@pytest.mark.parametrize("command", all_commands)
def test_aesthetic_help_msg(command):
    """All real commands help msgs start with uppercase and do not end with a dot."""
    msg = command.help_msg
    assert msg[0].isupper() and msg[-1] != "."


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
            assert help_msg[0].isupper() and help_msg[-1] != "."

    command(config).fill_parser(FakeParser())


@pytest.mark.parametrize("command_class", all_commands)
def test_usage_of_parsed_args(command_class, config):
    """The elements accesed on parsed_args need to be added before.

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
    tree = ast.parse(open(filepath, "rt").read())

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


def test_basecommand_needs_config_default():
    """A command by default does not needs config."""
    assert MySimpleCommand.needs_config is False


def test_basecommand_include_format_option(config):
    """Include a format option in the received parser."""
    parser = argparse.ArgumentParser()
    cmd = MySimpleCommand(config)
    cmd.include_format_option(parser)

    (action,) = [action for action in parser._actions if action.dest == "format"]
    assert action.option_strings == ["--format"]
    assert action.dest == "format"
    assert action.default is None
    assert action.choices == [JSON_FORMAT]
    assert action.help == "Produce the result formatted as a JSON string"


def test_basecommand_format_content_json(config):
    """Properly format content in JSON format."""
    data = ["foo", "bar"]
    cmd = MySimpleCommand(config)
    result = cmd.format_content(JSON_FORMAT, data)
    assert result == textwrap.dedent(
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
