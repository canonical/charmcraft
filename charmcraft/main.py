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

"""Main entry point module for all the tool functionality."""

import argparse
import sys
from collections import namedtuple

from charmcraft import config
from charmcraft.cmdbase import CommandError
from charmcraft.commands import build, clean, init, pack, store, version, analyze
from charmcraft.helptexts import help_builder
from charmcraft.parts import setup_parts


# XXX who should really do this?
import logging

_lib_loggers = [
    logging.getLogger("craft_providers"),
    logging.getLogger("craft_parts"),
    logging.getLogger("craft_store"),
]
for logger in _lib_loggers:
    logger.setLevel(logging.DEBUG)


# the summary of the whole program
GENERAL_SUMMARY = """
Charmcraft helps build, package and publish operators on Charmhub.

Together with the Python Operator Framework, charmcraft simplifies
operator development and collaboration.

See https://charmhub.io/publishing for more information.
"""


class ArgumentParsingError(Exception):
    """Exception used when an argument parsing error is found."""


class ProvideHelpException(Exception):
    """Exception used to provide help to the user."""


# Collect commands in different groups, for easier human consumption. Note that this is not
# declared in each command because it's much easier to do this separation/grouping in one
# central place and not distributed in several classes/files. Also note that order here is
# important when listing commands and showing help.
_basic_commands = [
    analyze.AnalyzeCommand,
    build.BuildCommand,
    clean.CleanCommand,
    pack.PackCommand,
    init.InitCommand,
    version.VersionCommand,
]
_charmhub_commands = [
    # auth
    store.LoginCommand,
    store.LogoutCommand,
    store.WhoamiCommand,
    # name handling
    store.RegisterCharmNameCommand,
    store.RegisterBundleNameCommand,
    store.ListNamesCommand,
    # pushing files and checking revisions
    store.UploadCommand,
    store.ListRevisionsCommand,
    # release process, and show status
    store.ReleaseCommand,
    store.StatusCommand,
    store.CloseCommand,
    # libraries support
    store.CreateLibCommand,
    store.PublishLibCommand,
    store.ListLibCommand,
    store.FetchLibCommand,
    # resources support
    store.ListResourcesCommand,
    store.UploadResourceCommand,
    store.ListResourceRevisionsCommand,
]
CommandGroup = namedtuple("CommandGroup", "name commands")
COMMAND_GROUPS = [
    CommandGroup("Basic", _basic_commands),
    CommandGroup("Charmhub", _charmhub_commands),
]


# global options: the name used internally, its type, short and long parameters, and help text
GlobalArgument = namedtuple("GlobalArgument", "name type short_option long_option help_message")
_DEFAULT_GLOBAL_ARGS = [
    GlobalArgument(
        "help",
        "flag",
        "-h",
        "--help",
        "Show this help message and exit",
    ),
    GlobalArgument(
        "verbose",
        "flag",
        "-v",
        "--verbose",
        "Show debug information and be more verbose",
    ),
    GlobalArgument(
        "quiet",
        "flag",
        "-q",
        "--quiet",
        "Only show warnings and errors, not progress",
    ),
]


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with custom error manager.."""

    def error(self, message):
        """Show the usage, the error message, and no more."""
        full_msg = help_builder.get_usage_message(message, command=self.prog)
        raise ArgumentParsingError(full_msg)


class Dispatcher:
    """Set up infrastructure and let the needed command run.

    ♪♫"Leeeeeet, the command ruuun"♪♫ https://www.youtube.com/watch?v=cv-0mmVnxPA
    """

    def __init__(self, commands_groups, extra_global_args=None):
        self.global_arguments = _DEFAULT_GLOBAL_ARGS[:]
        if extra_global_args is not None:
            self.global_arguments.extend(extra_global_args)

        self.commands = self._get_commands_info(commands_groups)
        self.command_class = None
        self.command_args = None
        self.loaded_command = None
        self.parsed_command_args = None

    def _get_commands_info(self, commands_groups):
        """Process the commands groups structure for easier programmable access."""
        commands = {}
        for command_group in commands_groups:
            for _cmd_class in command_group.commands:
                if _cmd_class.name in commands:
                    _stored_class = commands[_cmd_class.name]
                    raise RuntimeError(
                        "Multiple commands with same name: {} and {}".format(
                            _cmd_class.__name__, _stored_class.__name__
                        )
                    )
                commands[_cmd_class.name] = _cmd_class
        return commands

    def load_command(self, app_config):
        """Load a command."""
        self.loaded_command = self.command_class(app_config)

        # load and parse the command specific options/params
        parser = CustomArgumentParser(prog=self.loaded_command.name)
        self.loaded_command.fill_parser(parser)
        self.parsed_command_args = parser.parse_args(self.command_args)
        emit.trace(f"Command parsed sysargs: {self.parsed_command_args}")
        return self.loaded_command

    def _get_global_options(self):
        """Return the global flags ready to present in the help messages as options."""
        options = []
        for arg in self.global_arguments:
            options.append(("{}, {}".format(arg.short_option, arg.long_option), arg.help_message))
        return options

    def _get_general_help(self, *, detailed):
        """Produce the general application help."""
        options = self._get_global_options()
        if detailed:
            help_text = help_builder.get_detailed_help(options)
        else:
            help_text = help_builder.get_full_help(options)
        return help_text

    def _get_requested_help(self, parameters):
        """Produce the requested help depending on the rest of the command line params."""
        if len(parameters) == 0:
            # provide a general text when help was requested without parameters
            return self._get_general_help(detailed=False)
        if len(parameters) > 1:
            # too many parameters: provide a specific guiding error
            msg = (
                "Too many parameters when requesting help; "
                "pass a command, '--all', or leave it empty"
            )
            text = help_builder.get_usage_message(msg)
            raise ArgumentParsingError(text)

        # special parameter to get detailed help
        (param,) = parameters
        if param == "--all":
            # provide a detailed general help when this specific option was included
            return self._get_general_help(detailed=True)

        # at this point the parameter should be a command
        try:
            cmd_class = self.commands[param]
        except KeyError:
            msg = "command {!r} not found to provide help for".format(param)
            text = help_builder.get_usage_message(msg)
            raise ArgumentParsingError(text)

        # instantiate the command and fill its arguments
        command = cmd_class(None)
        parser = CustomArgumentParser(prog=command.name, add_help=False)
        command.fill_parser(parser)

        # produce the complete help message for the command
        options = self._get_global_options()
        for action in parser._actions:
            # store the different options if present, otherwise it's just the dest
            if action.option_strings:
                options.append((", ".join(action.option_strings), action.help))
            else:
                dest = action.dest if action.metavar is None else action.metavar
                options.append((dest, action.help))

        help_text = help_builder.get_command_help(command, options)
        return help_text

    def pre_parse_args(self, sysargs):
        """Pre-parse sys args.

        Several steps:

        - extract the global options and detects the possible command and its args

        - validate global options and apply them

        - validate that command is correct (NOT loading and parsing its arguments)
        """
        # get all arguments (default to what's specified) and those per options, to filter sysargs
        global_args = {}
        arg_per_option = {}
        options_with_equal = []
        for arg in self.global_arguments:
            arg_per_option[arg.short_option] = arg
            arg_per_option[arg.long_option] = arg
            if arg.type == "flag":
                default = False
            elif arg.type == "option":
                default = None
                options_with_equal.append(arg.long_option + "=")
            else:
                raise ValueError("Bad global args structure.")
            global_args[arg.name] = default

        filtered_sysargs = []
        sysargs = iter(sysargs)
        options_with_equal = tuple(options_with_equal)
        for sysarg in sysargs:
            if sysarg in arg_per_option:
                arg = arg_per_option[sysarg]
                if arg.type == "flag":
                    value = True
                else:
                    try:
                        value = next(sysargs)
                    except StopIteration:
                        raise ArgumentParsingError(
                            f"The {arg.name!r} option expects one argument."
                        )
                global_args[arg.name] = value
            elif sysarg.startswith(options_with_equal):
                option, value = sysarg.split("=", 1)
                if not value:
                    raise ArgumentParsingError(f"The {arg.name!r} option expects one argument.")
                arg = arg_per_option[option]
                global_args[arg.name] = value
            else:
                filtered_sysargs.append(sysarg)

        # control and use quiet/verbose options
        if global_args["quiet"] and global_args["verbose"]:
            raise ArgumentParsingError("The 'verbose' and 'quiet' options are mutually exclusive.")
        if global_args["quiet"]:
            emit.set_mode(EmitterMode.QUIET)
        elif global_args["verbose"]:
            emit.set_mode(EmitterMode.VERBOSE)
        emit.trace(f"Raw pre-parsed sysargs: args={ global_args} filtered={filtered_sysargs}")

        # handle requested help through -h/--help options
        if global_args["help"]:
            help_text = self._get_requested_help(filtered_sysargs)
            raise ProvideHelpException(help_text)

        if filtered_sysargs:
            command = filtered_sysargs[0]
            cmd_args = filtered_sysargs[1:]

            # handle requested help through implicit "help" command
            if command == "help":
                help_text = self._get_requested_help(cmd_args)
                raise ProvideHelpException(help_text)

            self.command_args = cmd_args
            try:
                self.command_class = self.commands[command]
            except KeyError:
                msg = "no such command {!r}".format(command)
                help_text = help_builder.get_usage_message(msg)
                raise ArgumentParsingError(help_text)
        else:
            # no command passed!
            help_text = self._get_general_help(detailed=False)
            raise ArgumentParsingError(help_text)

        emit.trace(f"General parsed sysargs: command={ command!r} args={cmd_args}")
        return global_args

    def run(self):
        """Really run the command."""
        return self.loaded_command.run(self.parsed_command_args)


def main(argv=None):
    """Provide the main entry point."""
    help_builder.init("charmcraft", GENERAL_SUMMARY, COMMAND_GROUPS)
    emit.init(EmitterMode.NORMAL, "charmcraft", f"Starting charmcraft version {__version__}")

    if argv is None:
        argv = sys.argv

    extra_global_options = [
        GlobalArgument(
            "project_dir",
            "option",
            "-p",
            "--project-dir",
            "Specify the project's directory (defaults to current)",
        ),
    ]

    # process
    try:
        env.ensure_charmcraft_environment_is_supported()
        setup_parts()

        # load the dispatcher and put everything in motion
        dispatcher = Dispatcher(COMMAND_GROUPS, extra_global_options)
        global_args = dispatcher.pre_parse_args(argv[1:])
        loaded_config = config.load(global_args["project_dir"])
        command = dispatcher.load_command(loaded_config)
        if command.needs_config and not loaded_config.project.config_provided:
            raise ArgumentParsingError(
                "The specified command needs a valid 'charmcraft.yaml' configuration file (in "
                "the current directory or where specified with --project-dir option); see "
                "the reference: https://discourse.charmhub.io/t/charmcraft-configuration/4138"
            )
        retcode = dispatcher.run()

    except ArgumentParsingError as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 1
    except ProvideHelpException as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 0
    except CommandError as err:
        emit.error(err)
        retcode = err.retcode
    except KeyboardInterrupt as exc:
        error = CraftError("Interrupted.")
        error.__cause__ = exc
        emit.error(error)
        retcode = 1
    except Exception as err:
        error = CraftError(f"charmcraft internal error: {err!r}")
        error.__cause__ = err
        emit.error(error)
        retcode = 1
    else:
        emit.ended_ok()
        if retcode is None:
            retcode = 0

    return retcode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
