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
import operator
import os
import sys

from charmcraft import __version__
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


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with grouped commands help."""

    # Flag to indicate action groups that will have custom docs
    special_group = object()

    def __init__(self, **kwargs):
        self.__commands_groups = kwargs.pop('commands_groups', ())
        super().__init__(**kwargs)

    def format_help(self):
        """Produce normal help, but with grouped commands."""
        main = False
        for ag in self._action_groups:
            if ag.title is self.special_group:
                self._action_groups.remove(ag)
                main = True
                break
        base = super().format_help()
        if not main:
            return base

        # Get the size of the longest name so all help texts are aligned
        # properly across the groups.
        longest_name = 0
        for _, _, cmd_classes in self.__commands_groups:
            for cmd_class in cmd_classes:
                longest_name = max(len(cmd_class.name), longest_name)

        extra = ['', 'commands:', '']
        for group, group_title, cmd_classes in self.__commands_groups:
            extra.append("    {}:".format(group_title))
            for cmd_class in sorted(cmd_classes, key=operator.attrgetter('name')):
                extra.append("        {:{longest}s}   {}".format(
                    cmd_class.name, cmd_class.help_msg, longest=longest_name))
            extra.append('')

        return base + '\n'.join(extra)


class Dispatcher:
    """Set up infrastructure and let the needed command run.

    ♪♫"Leeeeeet, the command ruuun"♪♫ https://www.youtube.com/watch?v=cv-0mmVnxPA
    """

    def __init__(self, sysargs, commands_groups):
        logger.debug("Starting charmcraft version %s", __version__)

        self.commands = self._load_commands(commands_groups)
        logger.debug("Commands loaded: %s", self.commands)

        self.main_parser = self._build_argument_parser(commands_groups)
        self.parsed_args = self.main_parser.parse_args(sysargs)
        logger.debug("Parsed arguments: %s", self.parsed_args)

    def run(self):
        """Really run the command."""
        self._handle_global_params()

        if not hasattr(self.parsed_args, '_command'):
            self.main_parser.print_help()
            return 1

        command = self.parsed_args._command
        command.run(self.parsed_args)

    def _handle_global_params(self):
        """Set up and process global parameters."""
        if self.parsed_args.verbose:
            message_handler.set_mode(message_handler.VERBOSE)
        elif self.parsed_args.quiet:
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

    def _add_global_options(self, parser):
        """Add the global options to the received parser."""
        mutexg = parser.add_mutually_exclusive_group()
        mutexg.add_argument(
            '-v', '--verbose', action='store_true',
            help="be more verbose and show debug information")
        mutexg.add_argument(
            '-q', '--quiet', action='store_true',
            help="only show warnings and errors, not progress")

    def _build_argument_parser(self, commands_groups):
        """Build the generic argument parser."""
        parser = CustomArgumentParser(
            prog='charmcraft',
            description="The main tool to build, upload, and develop in general the Juju Charms.",
            commands_groups=commands_groups)

        # basic general options
        self._add_global_options(parser)

        subparsers = parser.add_subparsers(title=CustomArgumentParser.special_group)
        for group_name, _, cmd_classes in commands_groups:
            for cmd_class in cmd_classes:
                name = cmd_class.name
                command = self.commands[name]

                subparser = subparsers.add_parser(
                    name, help=command.help_msg, description=command.overview,
                    formatter_class=argparse.RawDescriptionHelpFormatter)
                subparser.set_defaults(_command=command)
                self._add_global_options(subparser)
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
