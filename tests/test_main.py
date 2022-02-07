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

import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    CraftError,
    EmitterMode,
    ProvideHelpException,
)

from charmcraft import __version__, env
from charmcraft.cmdbase import BaseCommand
from charmcraft.main import COMMAND_GROUPS, main


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
        EmitterMode.NORMAL,
        "charmcraft",
        f"Starting charmcraft version {__version__}",
        log_filepath=None,
    )


def test_main_managed_instance(monkeypatch):
    """Init emitter with a specific log filepath."""
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")

    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = None
            main(["charmcraft", "version"])

    # check how Emitter was initted
    emit_mock.init.assert_called_once_with(
        EmitterMode.NORMAL,
        "charmcraft",
        f"Starting charmcraft version {__version__}",
        log_filepath=env.get_managed_environment_log_path(),
    )


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
        overview = "test overview"

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
        overview = "test overview"

        def run(self, parsed_args):
            assert self.config.type is None
            assert not self.config.project.config_provided

    with patch("charmcraft.main.COMMAND_GROUPS", [CommandGroup("title", [MyCommand])]):
        retcode = main(["charmcraft", "cmdname", "--project-dir=/whatever"])
    assert retcode == 0


def test_main_load_config_not_present_but_needed(capsys):
    """Command ends indicating the return code to be used."""

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


def test_main_controlled_error():
    """Work raised CraftError: message handler notified properly, use indicated return code."""
    simulated_exception = CraftError("boom", retcode=33)
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.side_effect = simulated_exception
            retcode = main(["charmcraft", "version"])

    assert retcode == 33
    emit_mock.error.assert_called_once_with(simulated_exception)


def test_main_controlled_return_code():
    """Work ended ok, and the command indicated the return code."""
    with patch("charmcraft.main.emit") as emit_mock:
        with patch("charmcraft.main.Dispatcher.run") as d_mock:
            d_mock.return_value = 9
            retcode = main(["charmcraft", "version"])

    assert retcode == 9
    emit_mock.ended_ok.assert_called_once_with()


def test_main_crash():
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


def test_main_interrupted():
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


def test_main_controlled_arguments_error(capsys):
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


def test_main_providing_help(capsys):
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


# -- generic tests for all Charmcraft commands

all_commands = list.__add__(*[cgroup.commands for cgroup in COMMAND_GROUPS])


@pytest.mark.parametrize("command", all_commands)
def test_commands(command):
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


def test_basecommand_needs_config_default():
    """A command by default does not needs config."""
    assert BaseCommand.needs_config is False
