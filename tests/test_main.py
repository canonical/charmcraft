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

import argparse
import io
import os
import pathlib
import subprocess
import sys
from unittest.mock import patch

from charmcraft import __version__, logsetup
from charmcraft.main import (
    _DEFAULT_GLOBAL_ARGS,
    ArgumentParsingError,
    COMMAND_GROUPS,
    CommandGroup,
    Dispatcher,
    GlobalArgument,
    ProvideHelpException,
    main,
)
from charmcraft.cmdbase import BaseCommand, CommandError
from tests.factory import create_command

import pytest


@pytest.fixture(autouse=True)
def mock_ensure_charmcraft_environment_is_supported(monkeypatch):
    """Bypass entry point check for running as snap."""
    with patch("charmcraft.env.ensure_charmcraft_environment_is_supported") as mock_supported:
        yield mock_supported


# --- Tests for the Dispatcher


def test_dispatcher_pre_parsing():
    """Parses and return global arguments."""
    groups = [CommandGroup("title", [create_command("somecommand")])]
    dispatcher = Dispatcher(groups)
    global_args = dispatcher.pre_parse_args(["-q", "somecommand"])
    assert global_args == {"help": False, "verbose": False, "quiet": True}


def test_dispatcher_command_loading():
    """Parses and return global arguments."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["somecommand"])
    command = dispatcher.load_command("test-config")
    assert isinstance(command, cmd)
    assert command.config == "test-config"


def test_dispatcher_command_execution_ok():
    """Command execution depends of the indicated name in command line, return code ok."""

    class MyCommandControl(BaseCommand):
        help_msg = "some help"

        def run(self, parsed_args):
            self._executed.append(parsed_args)

    class MyCommand1(MyCommandControl):
        name = "name1"
        _executed = []

    class MyCommand2(MyCommandControl):
        name = "name2"
        _executed = []

    groups = [CommandGroup("title", [MyCommand1, MyCommand2])]
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["name2"])
    dispatcher.load_command("config")
    dispatcher.run()
    assert MyCommand1._executed == []
    assert isinstance(MyCommand2._executed[0], argparse.Namespace)


def test_dispatcher_command_return_code():
    """Command ends indicating the return code to be used."""

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"

        def run(self, parsed_args):
            return 17

    groups = [CommandGroup("title", [MyCommand])]
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["cmdname"])
    dispatcher.load_command("config")
    retcode = dispatcher.run()
    assert retcode == 17


def test_dispatcher_command_execution_crash():
    """Command crashing doesn't pass through, we inform nicely."""

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"

        def run(self, parsed_args):
            raise ValueError()

    groups = [CommandGroup("title", [MyCommand])]
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["cmdname"])
    dispatcher.load_command("config")
    with pytest.raises(ValueError):
        dispatcher.run()


def test_dispatcher_generic_setup_default():
    """Generic parameter handling for default values."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    logsetup.message_handler.mode = None
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["somecommand"])
    assert logsetup.message_handler.mode is None


@pytest.mark.parametrize(
    "options",
    [
        ["somecommand", "--verbose"],
        ["somecommand", "-v"],
        ["-v", "somecommand"],
        ["--verbose", "somecommand"],
        ["--verbose", "somecommand", "-v"],
    ],
)
def test_dispatcher_generic_setup_verbose(options):
    """Generic parameter handling for verbose log setup, directly or after the command."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    logsetup.message_handler.mode = None
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(options)
    assert logsetup.message_handler.mode == logsetup.message_handler.VERBOSE


@pytest.mark.parametrize(
    "options",
    [
        ["somecommand", "--quiet"],
        ["somecommand", "-q"],
        ["-q", "somecommand"],
        ["--quiet", "somecommand"],
        ["--quiet", "somecommand", "-q"],
    ],
)
def test_dispatcher_generic_setup_quiet(options):
    """Generic parameter handling for quiet log setup, directly or after the command."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    logsetup.message_handler.mode = None
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(options)
    assert logsetup.message_handler.mode == logsetup.message_handler.QUIET


@pytest.mark.parametrize(
    "options",
    [
        ["--quiet", "--verbose", "somecommand"],
        ["-v", "-q", "somecommand"],
        ["somecommand", "--quiet", "--verbose"],
        ["somecommand", "-v", "-q"],
        ["--verbose", "somecommand", "--quiet"],
        ["-q", "somecommand", "-v"],
    ],
)
def test_dispatcher_generic_setup_mutually_exclusive(options):
    """Disallow mutually exclusive generic options."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    dispatcher = Dispatcher(groups)
    with pytest.raises(ArgumentParsingError) as err:
        dispatcher.pre_parse_args(options)
    assert str(err.value) == "The 'verbose' and 'quiet' options are mutually exclusive."


@pytest.mark.parametrize(
    "options",
    [
        ["somecommand", "--globalparam", "foobar"],
        ["somecommand", "--globalparam=foobar"],
        ["somecommand", "-g", "foobar"],
        ["-g", "foobar", "somecommand"],
        ["--globalparam", "foobar", "somecommand"],
        ["--globalparam=foobar", "somecommand"],
    ],
)
def test_dispatcher_generic_setup_paramglobal_with_param(options):
    """Generic parameter handling for a param type global arg, directly or after the cmd."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    extra = GlobalArgument("globalparam", "option", "-g", "--globalparam", "Test global param.")
    dispatcher = Dispatcher(groups, [extra])
    global_args = dispatcher.pre_parse_args(options)
    assert global_args["globalparam"] == "foobar"


@pytest.mark.parametrize(
    "options",
    [
        ["somecommand", "--globalparam"],
        ["somecommand", "--globalparam="],
        ["somecommand", "-g"],
        ["--globalparam=", "somecommand"],
    ],
)
def test_dispatcher_generic_setup_paramglobal_without_param_simple(options):
    """Generic parameter handling for a param type global arg without the requested parameter."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    extra = GlobalArgument("globalparam", "option", "-g", "--globalparam", "Test global param.")
    dispatcher = Dispatcher(groups, [extra])
    with pytest.raises(ArgumentParsingError) as err:
        dispatcher.pre_parse_args(options)
    assert str(err.value) == "The 'globalparam' option expects one argument."


@pytest.mark.parametrize(
    "options",
    [
        ["-g", "somecommand"],
        ["--globalparam", "somecommand"],
    ],
)
def test_dispatcher_generic_setup_paramglobal_without_param_confusing(options):
    """Generic parameter handling for a param type global arg confusing the command as the arg."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    extra = GlobalArgument("globalparam", "option", "-g", "--globalparam", "Test global param.")
    dispatcher = Dispatcher(groups, [extra])
    with patch("charmcraft.helptexts.HelpBuilder.get_full_help") as mock_helper:
        mock_helper.return_value = "help text"
        with pytest.raises(ArgumentParsingError) as err:
            dispatcher.pre_parse_args(options)

    # generic usage message because "no command" (as 'somecommand' was consumed by --globalparam)
    assert str(err.value) == "help text"


def test_dispatcher_build_commands_ok():
    """Correct command loading."""
    cmd0, cmd1, cmd2 = [create_command("cmd-name-{}".format(n), "cmd help") for n in range(3)]
    groups = [
        CommandGroup("whatever title", [cmd0]),
        CommandGroup("other title", [cmd1, cmd2]),
    ]
    dispatcher = Dispatcher(groups)
    assert len(dispatcher.commands) == 3
    for cmd in [cmd0, cmd1, cmd2]:
        expected_class = dispatcher.commands[cmd.name]
        assert expected_class == cmd


def test_dispatcher_build_commands_repeated():
    """Error while loading commands with repeated name."""

    class Foo(BaseCommand):
        help_msg = "some help"
        name = "repeated"

    class Bar(BaseCommand):
        help_msg = "some help"
        name = "cool"

    class Baz(BaseCommand):
        help_msg = "some help"
        name = "repeated"

    groups = [
        CommandGroup("whatever title", [Foo, Bar]),
        CommandGroup("other title", [Baz]),
    ]
    expected_msg = "Multiple commands with same name: (Foo|Baz) and (Baz|Foo)"
    with pytest.raises(RuntimeError, match=expected_msg):
        Dispatcher(groups)


def test_dispatcher_commands_are_not_loaded_if_not_needed():
    class MyCommand1(BaseCommand):
        """Expected to be executed."""

        name = "command1"
        help_msg = "some help"
        _executed = []

        def run(self, parsed_args):
            self._executed.append(parsed_args)

    class MyCommand2(BaseCommand):
        """Expected to not be instantiated, or parse args, or run."""

        name = "command2"
        help_msg = "some help"

        def __init__(self, *args):
            raise AssertionError

        def fill_parser(self, parser):
            raise AssertionError

        def run(self, parsed_args):
            raise AssertionError

    groups = [CommandGroup("title", [MyCommand1, MyCommand2])]
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["command1"])
    dispatcher.load_command("config")
    dispatcher.run()
    assert isinstance(MyCommand1._executed[0], argparse.Namespace)


def test_dispatcher_global_arguments_default():
    """The dispatcher uses the default global arguments."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]

    dispatcher = Dispatcher(groups)
    assert dispatcher.global_arguments == _DEFAULT_GLOBAL_ARGS


def test_dispatcher_global_arguments_extra_arguments():
    """The dispatcher uses the default global arguments."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]

    extra_arg = GlobalArgument("other", "flag", "-o", "--other", "Other stuff")
    dispatcher = Dispatcher(groups, extra_global_args=[extra_arg])
    assert dispatcher.global_arguments == _DEFAULT_GLOBAL_ARGS + [extra_arg]


# --- Tests for the main entry point

# In all the test methods below we patch Dispatcher.run so we don't really exercise any
# command machinery, even if we call to main using a real command (which is to just
# make argument parsing system happy).


def test_main_ok():
    """Work ended ok: message handler notified properly, return code in 0."""
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            retcode = main(["charmcraft", "version"])

    assert retcode == 0
    mh_mock.ended_ok.assert_called_once_with()


def test_main_load_config_ok(create_config):
    """Command is properly executed, after loading and receiving the config."""
    tmp_path = create_config(
        """
        type: charm
    """
    )

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"

        def run(self, parsed_args):
            assert self.config.type == "charm"

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", f"--project-dir={tmp_path}"])
    assert retcode == 0


def test_main_load_config_not_present_ok():
    """Command ends indicating the return code to be used."""

    class MyCommand(BaseCommand):
        help_msg = "some help"
        name = "cmdname"

        def run(self, parsed_args):
            assert self.config.type is None
            assert not self.config.project.config_provided

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", "--project-dir=/whatever"])
    assert retcode == 0


def test_main_load_config_not_present_but_needed(capsys):
    """Command ends indicating the return code to be used."""
    cmd = create_command("cmdname", needs_config_=True)
    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [cmd])]):
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


def test_main_controlled_error():
    """Work raised CommandError: message handler notified properly, use indicated return code."""
    simulated_exception = CommandError("boom", retcode=33)
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 33
    mh_mock.ended_cmderror.assert_called_once_with(simulated_exception)


def test_main_controlled_return_code():
    """Work ended ok, and the command indicated the return code."""
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = 9
            retcode = main(["charmcraft", "version"])

    assert retcode == 9
    mh_mock.ended_ok.assert_called_once_with()


def test_main_environment_is_supported_error(mock_ensure_charmcraft_environment_is_supported):
    mock_ensure_charmcraft_environment_is_supported.side_effect = CommandError("not supported!")
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    assert mh_mock.ended_cmderror.call_count == 1


def test_main_crash():
    """Work crashed: message handler notified properly, return code in 1."""
    simulated_exception = ValueError("boom")
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    mh_mock.ended_crash.assert_called_once_with(simulated_exception)


def test_main_interrupted():
    """Work interrupted: message handler notified properly, return code in 1."""
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = KeyboardInterrupt
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    assert mh_mock.ended_interrupt.call_count == 1


def test_main_controlled_arguments_error(capsys):
    """The execution failed because an argument parsing error."""
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = ArgumentParsingError("test error")
            retcode = main(["charmcraft", "version"])

    assert retcode == 1
    mh_mock.ended_ok.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert err == "test error\n"


def test_main_providing_help(capsys):
    """The execution ended up providing a help message."""
    with patch("charmcraft.main.message_handler") as mh_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = ProvideHelpException("nice and shiny help message")
            retcode = main(["charmcraft", "version"])

    assert retcode == 0
    mh_mock.ended_ok.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not out
    assert err == "nice and shiny help message\n"


# --- Tests for the bootstrap version message


def test_initmsg_default():
    """Without any option, the init msg only goes to disk."""
    cmd = create_command("somecommand")
    fake_stream = io.StringIO()
    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("whatever title", [cmd])]):
        with patch.object(logsetup.message_handler, "ended_ok") as ended_ok_mock:
            with patch.object(logsetup.message_handler._stderr_handler, "stream", fake_stream):
                main(["charmcraft", "somecommand"])

    # get the logfile first line before removing it
    ended_ok_mock.assert_called_once_with()
    logged_to_file = pathlib.Path(logsetup.message_handler._log_filepath).read_text()
    file_first_line = logged_to_file.split("\n")[0]
    logsetup.message_handler.ended_ok()

    # get the terminal first line
    captured = fake_stream.getvalue()
    terminal_first_line = captured.split("\n")[0]

    expected = "Starting charmcraft version " + __version__
    assert expected in file_first_line
    assert expected not in terminal_first_line


def test_initmsg_quiet():
    """In quiet mode, the init msg only goes to disk."""
    cmd = create_command("somecommand")
    fake_stream = io.StringIO()
    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("whatever title", [cmd])]):
        with patch.object(logsetup.message_handler, "ended_ok") as ended_ok_mock:
            with patch.object(logsetup.message_handler._stderr_handler, "stream", fake_stream):
                main(["charmcraft", "--quiet", "somecommand"])

    # get the logfile first line before removing it
    ended_ok_mock.assert_called_once_with()
    logged_to_file = pathlib.Path(logsetup.message_handler._log_filepath).read_text()
    file_first_line = logged_to_file.split("\n")[0]
    logsetup.message_handler.ended_ok()

    # get the terminal first line
    captured = fake_stream.getvalue()
    terminal_first_line = captured.split("\n")[0]

    expected = "Starting charmcraft version " + __version__
    assert expected in file_first_line
    assert expected not in terminal_first_line


def test_initmsg_verbose():
    """In verbose mode, the init msg goes both to disk and terminal."""
    cmd = create_command("somecommand")
    fake_stream = io.StringIO()
    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("whatever title", [cmd])]):
        with patch.object(logsetup.message_handler, "ended_ok") as ended_ok_mock:
            with patch.object(logsetup.message_handler._stderr_handler, "stream", fake_stream):
                main(["charmcraft", "--verbose", "somecommand"])

    # get the logfile first line before removing it
    ended_ok_mock.assert_called_once_with()
    logged_to_file = pathlib.Path(logsetup.message_handler._log_filepath).read_text()
    file_first_line = logged_to_file.split("\n")[0]
    logsetup.message_handler.ended_ok()

    # get the terminal first line
    captured = fake_stream.getvalue()
    terminal_first_line = captured.split("\n")[0]

    expected = "Starting charmcraft version " + __version__
    assert expected in file_first_line
    assert expected in terminal_first_line


@pytest.mark.parametrize(
    "cmd_name", [cmd.name for cgroup in COMMAND_GROUPS for cmd in cgroup.commands]
)
def test_commands(cmd_name):
    """Sanity validation of a command.

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

    external_command = [sys.executable, "-m", "charmcraft", cmd_name, "-h"]
    subprocess.run(external_command, check=True, env=env, stdout=subprocess.DEVNULL)
