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

import textwrap
from unittest.mock import patch

import pytest

from fake_craft_cli import helptexts, dispatcher
from fake_craft_cli.errors import ArgumentParsingError, ProvideHelpException
from fake_craft_cli.dispatcher import CommandGroup, Dispatcher

from tests.factory import create_command


@pytest.fixture
def help_builder():
    """Provide a clean and fresh help_builder instance, ensuring the module also has it."""
    help_builder = helptexts.help_builder = dispatcher.help_builder = helptexts.HelpBuilder()
    return help_builder


# -- bulding "usage" help


def test_get_usage_message_with_command(help_builder):
    """Check the general "usage" text passing a command."""
    help_builder.init("testapp", "general summary", [])
    text = help_builder.get_usage_message("bad parameter for build", "build")
    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp build -h' for help.

        Error: bad parameter for build
    """
    )
    assert text == expected


def test_get_usage_message_no_command(help_builder):
    """Check the general "usage" text when not passing a command."""
    help_builder.init("testapp", "general summary", [])
    text = help_builder.get_usage_message("missing a mandatory command")
    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp -h' for help.

        Error: missing a mandatory command
    """
    )
    assert text == expected


# -- bulding of the big help text outputs


def test_default_help_text(help_builder):
    """All different parts for the default help."""
    cmd1 = create_command("cmd1", "Cmd help which is very long but whatever.", common_=True)
    cmd2 = create_command("command-2", "Cmd help.", common_=True)
    cmd3 = create_command("cmd3", "Extremely " + "super crazy long " * 5 + " help.", common_=True)
    cmd4 = create_command("cmd4", "Some help.")
    cmd5 = create_command("cmd5", "More help.")
    cmd6 = create_command("cmd6-really-long", "More help.", common_=True)
    cmd7 = create_command("cmd7", "More help.")

    command_groups = [
        CommandGroup("group1", [cmd6, cmd2]),
        CommandGroup("group3", [cmd7]),
        CommandGroup("group2", [cmd3, cmd4, cmd5, cmd1]),
    ]
    fake_summary = textwrap.dedent(
        """
        This is the summary for
        the whole program.
    """
    )
    global_options = [
        ("-h, --help", "Show this help message and exit."),
        ("-q, --quiet", "Only show warnings and errors, not progress."),
    ]

    help_builder.init("testapp", fake_summary, command_groups)
    text = help_builder.get_full_help(global_options)

    expected = textwrap.dedent(
        """\
        Usage:
            testapp [help] <command>

        Summary:
            This is the summary for
            the whole program.

        Global options:
                  -h, --help:  Show this help message and exit.
                 -q, --quiet:  Only show warnings and errors, not progress.

        Starter commands:
                        cmd1:  Cmd help which is very long but whatever.
                        cmd3:  Extremely super crazy long super crazy long super
                               crazy long super crazy long super crazy long
                               help.
            cmd6-really-long:  More help.
                   command-2:  Cmd help.

        Commands can be classified as follows:
                      group1:  cmd6-really-long, command-2
                      group2:  cmd1, cmd3, cmd4, cmd5
                      group3:  cmd7

        For more information about a command, run 'testapp help <command>'.
        For a summary of all commands, run 'testapp help --all'.
    """
    )
    assert text == expected


def test_detailed_help_text(help_builder):
    """All different parts for the detailed help, showing all commands."""
    cmd1 = create_command("cmd1", "Cmd help which is very long but whatever.", common_=True)
    cmd2 = create_command("command-2", "Cmd help.", common_=True)
    cmd3 = create_command("cmd3", "Extremely " + "super crazy long " * 5 + " help.", common_=True)
    cmd4 = create_command("cmd4", "Some help.")
    cmd5 = create_command("cmd5", "More help.")
    cmd6 = create_command("cmd6-really-long", "More help.", common_=True)
    cmd7 = create_command("cmd7", "More help.")

    command_groups = [
        CommandGroup("Group 1 description", [cmd6, cmd2]),
        CommandGroup("Group 3 help text", [cmd7]),
        CommandGroup("Group 2 stuff", [cmd3, cmd4, cmd5, cmd1]),
    ]
    fake_summary = textwrap.dedent(
        """
        This is the summary for
        the whole program.
    """
    )
    global_options = [
        ("-h, --help", "Show this help message and exit."),
        ("-q, --quiet", "Only show warnings and errors, not progress."),
    ]

    help_builder.init("testapp", fake_summary, command_groups)
    text = help_builder.get_detailed_help(global_options)

    expected = textwrap.dedent(
        """\
        Usage:
            testapp [help] <command>

        Summary:
            This is the summary for
            the whole program.

        Global options:
                  -h, --help:  Show this help message and exit.
                 -q, --quiet:  Only show warnings and errors, not progress.

        Commands can be classified as follows:

        Group 1 description:
            cmd6-really-long:  More help.
                   command-2:  Cmd help.

        Group 3 help text:
                        cmd7:  More help.

        Group 2 stuff:
                        cmd3:  Extremely super crazy long super crazy long super
                               crazy long super crazy long super crazy long
                               help.
                        cmd4:  Some help.
                        cmd5:  More help.
                        cmd1:  Cmd help which is very long but whatever.

        For more information about a specific command, run 'testapp help <command>'.
    """
    )
    assert text == expected


def test_command_help_text_no_parameters(config, help_builder):
    """All different parts for a specific command help that doesn't have parameters."""
    overview = textwrap.dedent(
        """
        Quite some long text.

        Multiline!
    """
    )
    cmd1 = create_command("somecommand", "Command one line help.", overview_=overview)
    cmd2 = create_command("other-cmd-2", "Some help.")
    cmd3 = create_command("other-cmd-3", "Some help.")
    cmd4 = create_command("other-cmd-4", "Some help.")
    command_groups = [
        CommandGroup("group1", [cmd1, cmd2, cmd4]),
        CommandGroup("group2", [cmd3]),
    ]

    options = [
        ("-h, --help", "Show this help message and exit."),
        ("-q, --quiet", "Only show warnings and errors, not progress."),
        ("--name", "The name of the charm."),
        ("--revision", "The revision to release (defaults to latest)."),
    ]

    help_builder.init("testapp", "general summary", command_groups)
    text = help_builder.get_command_help(cmd1(config), options)

    expected = textwrap.dedent(
        """\
        Usage:
            testapp somecommand [options]

        Summary:
            Quite some long text.

            Multiline!

        Options:
             -h, --help:  Show this help message and exit.
            -q, --quiet:  Only show warnings and errors, not progress.
                 --name:  The name of the charm.
             --revision:  The revision to release (defaults to latest).

        See also:
            other-cmd-2
            other-cmd-4

        For a summary of all commands, run 'testapp help --all'.
    """
    )
    assert text == expected


def test_command_help_text_with_parameters(config, help_builder):
    """All different parts for a specific command help that has parameters."""
    overview = textwrap.dedent(
        """
        Quite some long text.
    """
    )
    cmd1 = create_command("somecommand", "Command one line help.", overview_=overview)
    cmd2 = create_command("other-cmd-2", "Some help.")
    command_groups = [
        CommandGroup("group1", [cmd1, cmd2]),
    ]

    options = [
        ("-h, --help", "Show this help message and exit."),
        ("name", "The name of the charm."),
        ("--revision", "The revision to release (defaults to latest)."),
        ("extraparam", "Another parameter.."),
        ("--other-option", "Other option."),
    ]

    help_builder.init("testapp", "general summary", command_groups)
    text = help_builder.get_command_help(cmd1(config), options)

    expected = textwrap.dedent(
        """\
        Usage:
            testapp somecommand [options] <name> <extraparam>

        Summary:
            Quite some long text.

        Options:
                -h, --help:  Show this help message and exit.
                --revision:  The revision to release (defaults to latest).
            --other-option:  Other option.

        See also:
            other-cmd-2

        For a summary of all commands, run 'testapp help --all'.
    """
    )
    assert text == expected


def test_command_help_text_loneranger(config, help_builder):
    """All different parts for a specific command that's the only one in its group."""
    overview = textwrap.dedent(
        """
        Quite some long text.
    """
    )
    cmd1 = create_command("somecommand", "Command one line help.", overview_=overview)
    cmd2 = create_command("other-cmd-2", "Some help.")
    command_groups = [
        CommandGroup("group1", [cmd1]),
        CommandGroup("group2", [cmd2]),
    ]

    options = [
        ("-h, --help", "Show this help message and exit."),
        ("-q, --quiet", "Only show warnings and errors, not progress."),
    ]

    help_builder.init("testapp", "general summary", command_groups)
    text = help_builder.get_command_help(cmd1(config), options)

    expected = textwrap.dedent(
        """\
        Usage:
            testapp somecommand [options]

        Summary:
            Quite some long text.

        Options:
             -h, --help:  Show this help message and exit.
            -q, --quiet:  Only show warnings and errors, not progress.

        For a summary of all commands, run 'testapp help --all'.
    """
    )
    assert text == expected


# -- real execution outputs


def test_tool_exec_no_arguments_help():
    """Execute the app without any option at all."""
    dispatcher = Dispatcher("testapp", [])
    with patch("fake_craft_cli.helptexts.HelpBuilder.get_full_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ArgumentParsingError) as cm:
            dispatcher.pre_parse_args([])
    error = cm.value

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert sorted(x[0] for x in args[0]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]

    # check the result of the full help builder is what is shown
    assert str(error) == "test help"


@pytest.mark.parametrize(
    "sysargv",
    [
        ["-h"],
        ["--help"],
        ["help"],
    ],
)
def test_tool_exec_full_help(sysargv):
    """Execute the app explicitly asking for help."""
    dispatcher = Dispatcher("testapp", [])
    with patch("fake_craft_cli.helptexts.HelpBuilder.get_full_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(sysargv)

    # check the result of the full help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert sorted(x[0] for x in args[0]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]


def test_tool_exec_command_incorrect(help_builder):
    """Execute a command that doesn't exist."""
    dispatcher = Dispatcher("testapp", [], summary="general summary")
    with pytest.raises(ArgumentParsingError) as cm:
        dispatcher.pre_parse_args(["wrongcommand"])

    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp -h' for help.

        Error: no such command 'wrongcommand'
        """
    )

    error = cm.value
    assert str(error) == expected


@pytest.mark.parametrize(
    "sysargv",
    [
        ["-h", "wrongcommand"],
        ["wrongcommand", "-h"],
        ["--help", "wrongcommand"],
        ["wrongcommand", "--help"],
        ["-h", "wrongcommand", "--help"],
    ],
)
def test_tool_exec_help_on_command_incorrect(sysargv, help_builder):
    """Execute a command that doesn't exist."""
    dispatcher = Dispatcher("testapp", [], summary="general summary")
    with pytest.raises(ArgumentParsingError) as cm:
        dispatcher.pre_parse_args(sysargv)

    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp -h' for help.

        Error: command 'wrongcommand' not found to provide help for
        """
    )

    error = cm.value
    assert str(error) == expected


@pytest.mark.parametrize(
    "sysargv",
    [
        ["-h", "foo", "bar"],
        ["foo", "-h", "bar"],
        ["foo", "bar", "-h"],
        ["--help", "foo", "bar"],
        ["foo", "--help", "bar"],
        ["foo", "bar", "--help"],
        ["help", "foo", "bar"],
    ],
)
def test_tool_exec_help_on_too_many_things(sysargv, help_builder):
    """Trying to get help on too many items."""
    dispatcher = Dispatcher("testapp", [], summary="general summary")
    with pytest.raises(ArgumentParsingError) as cm:
        dispatcher.pre_parse_args(sysargv)

    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp -h' for help.

        Error: Too many parameters when requesting help; pass a command, '--all', or leave it empty
        """
    )

    error = cm.value
    assert str(error) == expected


@pytest.mark.parametrize("help_option", ["-h", "--help"])
def test_tool_exec_command_dash_help_simple(help_option):
    """Execute a command (that needs no params) asking for help."""
    cmd = create_command("somecommand", "This command does that.")
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_command_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(["somecommand", help_option])

    # check the result of the full help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert args[0].__class__ == cmd
    assert sorted(x[0] for x in args[1]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]


@pytest.mark.parametrize("help_option", ["-h", "--help"])
def test_tool_exec_command_dash_help_reverse(help_option):
    """Execute a command (that needs no params) asking for help."""
    cmd = create_command("somecommand", "This command does that.")
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_command_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args([help_option, "somecommand"])

    # check the result of the full help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert args[0].__class__ == cmd
    assert sorted(x[0] for x in args[1]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]


@pytest.mark.parametrize("help_option", ["-h", "--help"])
def test_tool_exec_command_dash_help_missing_params(help_option):
    """Execute a command (which needs params) asking for help."""

    def fill_parser(self, parser):
        parser.add_argument("mandatory")

    cmd = create_command("somecommand", "This command does that.")
    cmd.fill_parser = fill_parser
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_command_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(["somecommand", help_option])

    # check the result of the full help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert args[0].__class__ == cmd
    assert sorted(x[0] for x in args[1]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
        "mandatory",
    ]


def test_tool_exec_command_wrong_option(help_builder):
    """Execute a correct command but with a wrong option."""
    cmd = create_command("somecommand", "This command does that.")
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups, summary="general summary")
    dispatcher.pre_parse_args(["somecommand", "--whatever"])

    with pytest.raises(ArgumentParsingError) as cm:
        dispatcher.load_command("config")

    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp somecommand -h' for help.

        Error: unrecognized arguments: --whatever
        """
    )

    error = cm.value
    assert str(error) == expected


def test_tool_exec_command_bad_option_type(help_builder):
    """Execute a correct command but giving the valid option a bad value."""

    def fill_parser(self, parser):
        parser.add_argument("--number", type=int)

    cmd = create_command("somecommand", "This command does that.")
    cmd.fill_parser = fill_parser

    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups, summary="general summary")
    dispatcher.pre_parse_args(["somecommand", "--number=foo"])

    with pytest.raises(ArgumentParsingError) as cm:
        dispatcher.load_command("config")

    expected = textwrap.dedent(
        """\
        Usage: testapp [options] command [args]...
        Try 'testapp somecommand -h' for help.

        Error: argument --number: invalid int value: 'foo'
        """
    )

    error = cm.value
    assert str(error) == expected


def test_tool_exec_help_command_on_command_ok():
    """Execute the app asking for help on a command ok."""
    cmd = create_command("somecommand", "This command does that.")
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_command_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(["help", "somecommand"])

    # check the result of the help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert isinstance(args[0], cmd)
    assert sorted(x[0] for x in args[1]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]


def test_tool_exec_help_command_on_command_complex():
    """Execute the app asking for help on a command with parameters and options."""

    def fill_parser(self, parser):
        parser.add_argument("param1", help="help on param1")
        parser.add_argument("param2", help="help on param2")
        parser.add_argument("param3", metavar="transformed3", help="help on param2")
        parser.add_argument("--option1", help="help on option1")
        parser.add_argument("-o2", "--option2", help="help on option2")

    cmd = create_command("somecommand", "This command does that.")
    cmd.fill_parser = fill_parser
    command_groups = [CommandGroup("group", [cmd])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_command_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(["help", "somecommand"])

    # check the result of the help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert args[0].__class__ == cmd
    expected_options = [
        "--option1",
        "-h, --help",
        "-o2, --option2",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
        "param1",
        "param2",
        "transformed3",
    ]
    assert sorted(x[0] for x in args[1]) == expected_options


def test_tool_exec_help_command_on_command_wrong():
    """Execute the app asking for help on a command which does not exist."""
    command_groups = [CommandGroup("group", [])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_usage_message") as mock:
        mock.return_value = "test help"
        with pytest.raises(ArgumentParsingError) as cm:
            dispatcher.pre_parse_args(["help", "wrongcommand"])
    error = cm.value

    # check the given information to the help text builder
    assert mock.call_args[0] == ("command 'wrongcommand' not found to provide help for",)

    # check the result of the help builder is what is shown
    assert str(error) == "test help"


def test_tool_exec_help_command_all():
    """Execute the app asking for detailed help."""
    command_groups = [CommandGroup("group", [])]
    dispatcher = Dispatcher("testapp", command_groups)

    with patch("fake_craft_cli.helptexts.HelpBuilder.get_detailed_help") as mock:
        mock.return_value = "test help"
        with pytest.raises(ProvideHelpException) as cm:
            dispatcher.pre_parse_args(["help", "--all"])

    # check the result of the help builder is what is transmitted
    assert str(cm.value) == "test help"

    # check the given information to the help text builder
    args = mock.call_args[0]
    assert sorted(x[0] for x in args[0]) == [
        "-h, --help",
        "-q, --quiet",
        "-t, --trace",
        "-v, --verbose",
    ]
