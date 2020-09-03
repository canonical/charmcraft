# Copyright 2020 Canonical Ltd.
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
import logging
import os
import sys

from charmcraft import helptexts
from charmcraft.commands import version, build, store, init
from charmcraft.cmdbase import CommandError
from charmcraft.logsetup import message_handler

logger = logging.getLogger(__name__)


# Collect commands in different groups, for easier human consumption. Note that this is not
# declared in each command because it's much easier to do this separation/grouping in one
# central place and not distributed in several classes/files.
COMMAND_GROUPS = [
    ('basic', "basics", [version.VersionCommand, build.BuildCommand, init.InitCommand]),
    ('store', "interaction with the store", [
        # auth
        store.LoginCommand, store.LogoutCommand, store.WhoamiCommand,
        # name handling
        store.RegisterNameCommand, store.ListNamesCommand,
        # pushing files and checking revisions
        store.UploadCommand, store.ListRevisionsCommand,
        # release process, and show status
        store.ReleaseCommand, store.StatusCommand,
    ]),
]


def _get_option(args, name):
    """Get a general option, merging with OR both global and command versions.

    This is done manually because otherwise Argparse would overwrite the
    command ont into thee global one.
    """
    return getattr(args, name + '_global', False) or getattr(args, name + '_command', False)


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with grouped commands help."""

    def __init__(self, **kwargs):
        self._command_parser = kwargs.pop('command_parser', False)  #FIXME: need tihs?
        super().__init__(**kwargs)

    def parse_known_args(self, args, namespace):
        """Hold the namespace to verify if help was requested."""
        print("======== parse known args", self, args, namespace)
        if namespace is None:
            namespace = argparse.Namespace()
        self._namespace = namespace
        return super().parse_known_args(args, namespace)

    #def print_help(*args):
    #    print("================== print help", args)
    #    super().print_help(*args)
    #def print_usage(*args):
    #    print("================== print usage", args)
    #    super().print_usage(*args)

    def _check_value(self, action, value):
        """Verify the command is a valid one.

        This overwrites ArgumentParser one to change the error text.
        """
        if action.choices is not None and value not in action.choices:
            raise argparse.ArgumentError(action, "no such command {!r}".format(value))

    def error(self, message):
        """Show the usage, the error message, and no more."""
        print("========== ERROR!", repr(message), self._namespace)
        # if help was requested, no matter other errors (just provide help!)
        if _get_option(self._namespace, 'help'):
            #FIXME refactor
            help_text = get_help(self, self._namespace)
            raise CommandError(help_text, argsparsing=True)

        #FIXME: join with below
        fullcommand = self.prog
        command = getattr(self._namespace, '_command', None)
        if command:
            subactions = [action for action in self._actions if isinstance(action, argparse._SubParsersAction)]
            if subactions:
                (subparseraction,) = subactions
                parser = subparseraction.choices[command.name]
                fullcommand = parser.prog

        full_msg = helptexts.get_error_message(fullcommand, message)
        raise CommandError(full_msg, argsparsing=True)


def get_help(parser, namespace):
    """Produce the complete (but not extensive) help message."""
    # we get here in three situations, for which we need different information
    # - no command given: then 'command' is None, the received parser is just the global one
    # - a command is given and asked for help: 'command' is the given command, we need to
    #   get the subparser to present the help for the given command
    # - a command is given but without a needed param: 'command' is the given command, and the
    #   parser is already the one for the command (the "subparser")
    command = getattr(namespace, '_command', None)
    print("=========== namespace", namespace)
    print("=========== actions", parser._actions)
    if command is not None:
        # if there is a subparser, replace the generic parser for that one
        subactions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
        if subactions:
            (subparseraction,) = subactions
            parser = subparseraction.choices[command.name]
    print("=========== redones", parser._actions)

    # get options from the global or command-specific parser
    actions = [
        action for action in parser._actions
        if not isinstance(action, argparse._SubParsersAction)]
    options = []
    for action in actions:
        # store the different options if present, otherwise it's just the dest
        if action.option_strings:
            options.append((', '.join(action.option_strings), action.help))
        else:
            options.append((action.dest, action.help))

    # get general or specific help
    if command is None:
        help_text = helptexts.get_full_help(COMMAND_GROUPS, options)
    else:
        help_text = helptexts.get_command_help(COMMAND_GROUPS, command, options)

    return help_text


class Dispatcher:
    """Set up infrastructure and let the needed command run.

    ♪♫"Leeeeeet, the command ruuun"♪♫ https://www.youtube.com/watch?v=cv-0mmVnxPA
    """

    def __init__(self, sysargs, commands_groups):
        self.commands = self._load_commands(commands_groups)
        logger.debug("Commands loaded: %s", self.commands)

        self.main_parser = self._build_argument_parser(commands_groups)
        self.parsed_args = self.main_parser.parse_args(sysargs)
        logger.debug("Parsed arguments: %s", self.parsed_args)

    def run(self):
        """Really run the command."""
        print("======= parsed args", self.parsed_args)
        self._handle_global_params()

        if not hasattr(self.parsed_args, '_command') or _get_option(self.parsed_args, 'help'):
            help_text = get_help(self.main_parser, self.parsed_args)
            raise CommandError(help_text, argsparsing=True)

        command = self.parsed_args._command
        command.run(self.parsed_args)

    def _handle_global_params(self):
        """Set up and process global parameters."""
        if _get_option(self.parsed_args, 'verbose'):
            message_handler.set_mode(message_handler.VERBOSE)
        if _get_option(self.parsed_args, 'quiet'):
            message_handler.set_mode(message_handler.QUIET)

    def _load_commands(self, commands_groups):
        """Init the commands and store them by name."""
        result = {}
        for cmd_group, _, cmd_classes in commands_groups:
            for cmd_class in cmd_classes:
                if cmd_class.name in result:
                    raise RuntimeError(
                        "Multiple commands with same name: {} and {}".format(
                            cmd_class.__name__, result[cmd_class.name].__class__.__name__))
                result[cmd_class.name] = cmd_class(cmd_group)
        return result

    def _add_global_options(self, parser, context):
        """Add the global options to the received parser."""
        parser.add_argument(
            '-h', '--help', action='store_true', dest='help_' + context,
            help="Show this help message and exit.")
        mutexg = parser.add_mutually_exclusive_group()
        mutexg.add_argument(
            '-v', '--verbose', action='store_true', dest='verbose_' + context,
            help="be more verbose and show debug information")
        mutexg.add_argument(
            '-q', '--quiet', action='store_true', dest='quiet_' + context,
            help="only show warnings and errors, not progress")

    def _build_argument_parser(self, commands_groups):
        """Build the generic argument parser."""
        parser = CustomArgumentParser(
            description="The main tool to build, upload and develop in general the Juju Charms.",
            prog='charmcraft', add_help=False)

        self._add_global_options(parser, 'global')

        subparsers = parser.add_subparsers()
        for group_name, _, cmd_classes in commands_groups:
            for cmd_class in cmd_classes:
                name = cmd_class.name
                command = self.commands[name]

                subparser = subparsers.add_parser(
                    name, help=command.help_msg, command_parser=True, add_help=False)
                subparser.set_defaults(_command=command)
                self._add_global_options(subparser, 'command')
                command.fill_parser(subparser)

        return parser


def main(argv=None):
    """Main entry point."""
    # Setup logging, using DEBUG envvar in case dev wants to show info before
    # command parsing.
    mode = message_handler.VERBOSE if 'DEBUG' in os.environ else message_handler.NORMAL
    message_handler.init(mode)

    if argv is None:
        argv = sys.argv

    # process
    try:
        dispatcher = Dispatcher(argv[1:], COMMAND_GROUPS)
        dispatcher.run()
    except CommandError as err:
        message_handler.ended_cmderror(err)
        retcode = err.retcode
    except KeyboardInterrupt:
        message_handler.ended_interrupt()
        retcode = 1
    except Exception as err:
        message_handler.ended_crash(err)
        retcode = 1
    else:
        message_handler.ended_ok()
        retcode = 0

    return retcode


if __name__ == '__main__':
    sys.exit(main(sys.argv))
