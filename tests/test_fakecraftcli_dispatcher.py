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
from unittest.mock import patch

import pytest

from craft_cli import emit, EmitterMode
from fake_craft_cli.dispatcher import (
    _DEFAULT_GLOBAL_ARGS,
    BaseCommand,
    CommandGroup,
    Dispatcher,
    GlobalArgument,
)
from fake_craft_cli.errors import ArgumentParsingError
from tests.factory import create_command


# --- Tests for the Dispatcher


def test_dispatcher_pre_parsing():
    """Parses and return global arguments."""
    groups = [CommandGroup("title", [create_command("somecommand")])]
    dispatcher = Dispatcher(groups)
    global_args = dispatcher.pre_parse_args(["-q", "somecommand"])
    assert global_args == {"help": False, "verbose": False, "quiet": True, "trace": False}


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
        overview = "fake overview"

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
        overview = "fake overview"

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
        overview = "fake overview"

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
    emit.set_mode(EmitterMode.NORMAL)  # this is how `main` will init the Emitter
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(["somecommand"])
    assert emit.get_mode() == EmitterMode.NORMAL


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
    emit.set_mode(EmitterMode.NORMAL)  # this is how `main` will init the Emitter
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(options)
    assert emit.get_mode() == EmitterMode.VERBOSE


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
    emit.set_mode(EmitterMode.NORMAL)  # this is how `main` will init the Emitter
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(options)
    assert emit.get_mode() == EmitterMode.QUIET


@pytest.mark.parametrize(
    "options",
    [
        ["somecommand", "--trace"],
        ["somecommand", "-t"],
        ["-t", "somecommand"],
        ["--trace", "somecommand"],
        ["--trace", "somecommand", "-t"],
    ],
)
def test_dispatcher_generic_setup_trace(options):
    """Generic parameter handling for trace log setup, directly or after the command."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    emit.set_mode(EmitterMode.NORMAL)  # this is how `main` will init the Emitter
    dispatcher = Dispatcher(groups)
    dispatcher.pre_parse_args(options)
    assert emit.get_mode() == EmitterMode.TRACE


@pytest.mark.parametrize(
    "options",
    [
        ["--quiet", "--verbose", "somecommand"],
        ["-v", "-q", "somecommand"],
        ["somecommand", "--quiet", "--verbose"],
        ["somecommand", "-v", "-q"],
        ["--verbose", "somecommand", "--quiet"],
        ["-q", "somecommand", "-v"],
        ["--trace", "--verbose", "somecommand"],
        ["-v", "-t", "somecommand"],
        ["somecommand", "--trace", "--verbose"],
        ["somecommand", "-v", "-t"],
        ["--verbose", "somecommand", "--trace"],
        ["-t", "somecommand", "-v"],
        ["--quiet", "--trace", "somecommand"],
        ["-t", "-q", "somecommand"],
        ["somecommand", "--quiet", "--trace"],
        ["somecommand", "-t", "-q"],
        ["--trace", "somecommand", "--quiet"],
        ["-q", "somecommand", "-t"],
    ],
)
def test_dispatcher_generic_setup_mutually_exclusive(options):
    """Disallow mutually exclusive generic options."""
    cmd = create_command("somecommand")
    groups = [CommandGroup("title", [cmd])]
    dispatcher = Dispatcher(groups)
    with pytest.raises(ArgumentParsingError) as err:
        dispatcher.pre_parse_args(options)
    assert str(err.value) == "The 'verbose', 'trace' and 'quiet' options are mutually exclusive."


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
    with patch("fake_craft_cli.helptexts.HelpBuilder.get_full_help") as mock_helper:
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
        overview = "fake overview"
        _executed = []

        def run(self, parsed_args):
            self._executed.append(parsed_args)

    class MyCommand2(BaseCommand):
        """Expected to not be instantiated, or parse args, or run."""

        name = "command2"
        help_msg = "some help"
        overview = "fake overview"

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


# --- Tests for the base command


def test_basecommand_holds_the_indicated_info():
    """BaseCommand subclasses ."""

    class TestClass(BaseCommand):
        help_msg = "help message"
        name = "test"
        overview = "fake overview"

    config = "test config"
    tc = TestClass(config)
    assert tc.config == config


def test_basecommand_fill_parser_optional():
    """BaseCommand subclasses are allowed to not override fill_parser."""

    class TestClass(BaseCommand):
        help_msg = "help message"
        name = "test"
        overview = "fake overview"

        def __init__(self, config):
            self.done = False
            super().__init__(config)

        def run(self, parsed_args):
            self.done = True

    tc = TestClass("config")
    tc.run([])
    assert tc.done


def test_basecommand_run_mandatory():
    """BaseCommand subclasses must override run."""

    class TestClass(BaseCommand):
        help_msg = "help message"
        name = "test"
        overview = "fake overview"

    tc = TestClass("config")
    with pytest.raises(NotImplementedError):
        tc.run([])


def test_basecommand_mandatory_attribute_name():
    """BaseCommand subclasses must override the name attribute."""

    class TestClass(BaseCommand):
        help_msg = "help message"
        overview = "fake overview"

    with pytest.raises(TypeError):
        TestClass("config")


def test_basecommand_mandatory_attribute_help_message():
    """BaseCommand subclasses must override the help_message attribute."""

    class TestClass(BaseCommand):
        overview = "fake overview"
        name = "test"

    with pytest.raises(TypeError):
        TestClass("config")


def test_basecommand_mandatory_attribute_overview():
    """BaseCommand subclasses must override the overview attribute."""

    class TestClass(BaseCommand):
        help_msg = "help message"
        name = "test"

    with pytest.raises(TypeError):
        TestClass("config")
