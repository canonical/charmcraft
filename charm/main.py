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
# For further info, check https://github.com/canonical/charm


import argparse
import logging
import os
import sys

from charm import logsetup

logger = logging.getLogger(__name__)


class CommandError(Exception):
    """Base exception for all error commands.

    It optionally receives an `retcode` parameter that will be the returned code
    by the process on exit.
    """
    def __init__(self, message, retcode=-1):
        self.retcode = retcode
        super().__init__(message)


class BaseCommand:

    name = None
    help_msg = None

    def __init__(self, group):
        if self.name is None or self.help_msg is None:
            raise RuntimeError("Command not properly created: {!r}".format(self.__class__))
        self.group = group

    def fill_parser(self, parser):
        """Overwrite in each command and fill the parser with command-specific parameters.

        If not overwritten, the command will not have any parameters.
        """


class VersionCommand(BaseCommand):
    """Show the version."""
    name = 'version'
    help_msg = "show the version"

    def run(self, parsed_args):
        """Run the command."""
        # XXX: we need to define how we want to store the project version (in config/file/etc.)
        version = '0.0.1'
        logger.info('Version: %s', version)


# XXX: while VersionCommand above probably would stay here, the other commands surely will
# be located in different files... that said, I'm keeping these examples here, for
# simplicitiy


class CommandExampleDebug(BaseCommand):
    """Just an example."""

    name = 'example-debug'
    help_msg = "show msg in debug"

    def fill_parser(self, parser):
        parser.add_argument('foo')
        parser.add_argument('--bar', action='store_true', help="To use this command in a bar")

    def run(self, parsed_args):
        logger.debug(
            "Example showing log in DEBUG: foo=%s bar=%s", parsed_args.foo, parsed_args.bar)


class CommandExampleError(BaseCommand):
    """Just an example."""

    name = 'example-error'
    help_msg = "show msg in error"

    def run(self, parsed_args):
        logger.error("Example showing log in ERROR.")


# Collect commands in different groups, for easier human consumption. Note that this is not
# declared in each command because it's much easier to do this separation/grouping in one
# central place and not distributed in several classes/files.
COMMANDS_GROUPS = [
    ('basic', [VersionCommand, CommandExampleError]),
    ('advanced', [CommandExampleDebug]),
]


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with grouped commands help."""
    # XXX: we should find a better way of doing this

    def format_help(self):
        """SUPER HACKY help."""
        main = False
        for ag in self._action_groups:
            if ag.title == 'MARKER':
                self._action_groups.remove(ag)
                main = True
                break
        base = super().format_help()
        if not main:
            return base

        extra = ['', 'commands:', '']
        for group, cmd_classes in COMMANDS_GROUPS:
            extra.append("    title for {!r}:".format(group))
            for cmd_class in cmd_classes:
                extra.append("        {:20s} {}".format(cmd_class.name, cmd_class.help_msg))
            extra.append('')

        return base + '\n'.join(extra)


class Dispatcher:
    """Set up infrastructure and let the needed command run.

    ♪♫"Leeeeeet, the command ruuun"♪♫ https://www.youtube.com/watch?v=cv-0mmVnxPA
    """

    def __init__(self, sysargs):
        self.commands = self._load_commands(COMMANDS_GROUPS)
        logger.debug("Commands loaded: %s", self.commands)

        self.main_parser = self._build_argument_parser()
        self.parsed_args = self.main_parser.parse_args(sysargs)
        logger.debug("Parsed arguments: %s", self.parsed_args)

    def run(self):
        """Really run the command."""
        self._handle_generics()

        if not hasattr(self.parsed_args, '_command'):
            self.main_parser.print_help()
            return -1

        command = self.parsed_args._command
        try:
            command.run(self.parsed_args)
        except CommandError as err:
            return err.retcode
        return 0

    def _handle_generics(self):
        """Set up and process generics."""
        if self.parsed_args.verbose:
            logsetup.configure('verbose')
        elif self.parsed_args.quiet:
            logsetup.configure('quiet')

    def _load_commands(self, commands_groups):
        """Init the commands and store them by name."""
        result = {}
        for cmd_group, cmd_classes in commands_groups:
            for cmd_class in cmd_classes:
                if cmd_class.name in result:
                    raise RuntimeError(
                        "Multiple commands with same name: {} and {}".format(
                            cmd_class, result[cmd_class.name].__class__))
                result[cmd_class.name] = cmd_class(cmd_group)
        return result

    def _build_argument_parser(self):
        """Build the generic argument parser."""
        parser = CustomArgumentParser(
            prog='charm',
            description="The main tool to build, upload, and develop in general the Juju charms.")

        # basic general options
        me = parser.add_mutually_exclusive_group()
        me.add_argument('-v', '--verbose', action='store_true', help="be more verbose")
        me.add_argument('-q', '--quiet', action='store_true', help="shh!")

        subparsers = parser.add_subparsers(title="MARKER")
        for group_name, cmd_classes in COMMANDS_GROUPS:
            for cmd_class in cmd_classes:
                name = cmd_class.name
                command = self.commands[name]

                subparser = subparsers.add_parser(name, help=command.help_msg)
                subparser.set_defaults(_command=command)
                command.fill_parser(subparser)

        return parser


def main():
    """Main entry point."""
    # Setup logging, using DEBUG envvar in case dev wants to show info before
    # command parsing.
    mode = 'verbose' if 'DEBUG' in os.environ else 'normal'
    logsetup.configure(mode)

    # process
    dispatcher = Dispatcher(sys.argv[1:])
    sys.exit(dispatcher.run())


if __name__ == '__main__':
    main()
