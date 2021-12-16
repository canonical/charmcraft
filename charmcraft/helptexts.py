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

"""Provide all help texts."""

import textwrap
from operator import attrgetter

# max columns used in the terminal
TERMINAL_WIDTH = 72

# generic intro and outro texts
HEADER = """
Usage:
    {appname} [help] <command>
"""

USAGE = """\
Usage: {appname} [options] command [args]...
Try '{full_command} -h' for help.

Error: {error_message}
"""


def _build_item(title, text, title_space):
    """Show an item in the help, generically a title and a text aligned.

    The title starts in column 4 with an extra ':'. The text starts in
    4 plus the title space; if too wide it's wrapped.
    """
    # wrap the general text to the desired max width (discounting the space for the title,
    # the first 4 spaces, the two spaces to separate title/text, and the ':'
    not_title_space = 7
    text_space = TERMINAL_WIDTH - title_space - not_title_space
    wrapped_lines = textwrap.wrap(text, text_space)

    # first line goes with the title at column 4
    first = "    {:>{title_space}s}:  {}".format(title, wrapped_lines[0], title_space=title_space)
    result = [first]

    # the rest (if any) still aligned but without title
    for line in wrapped_lines[1:]:
        result.append(" " * (title_space + not_title_space) + line)

    return result


class HelpBuilder:
    """Produce the different help texts."""

    def __init__(self):
        self.appname = None
        self.general_summary = None
        self.command_groups = None

    def init(self, appname, general_summary, command_groups):
        """Init the helper."""
        self.appname = appname
        self.general_summary = general_summary
        self.command_groups = command_groups

    def get_usage_message(self, error_message, command=""):
        """Build a usage and error message.

        The command is the extra string used after the application name to build the
        full command that will be shown in the usage message; for example, having an
        application name of "someapp":
        - if command is "" it will be shown "Try 'appname -h' for help".
        - if command is "version" it will be shown "Try 'appname version -h' for help"

        The error message is the specific problem in the given parameters.
        """
        if command:
            full_command = f"{self.appname} {command}"
        else:
            full_command = self.appname
        return USAGE.format(
            appname=self.appname, full_command=full_command, error_message=error_message
        )

    def get_full_help(self, global_options):
        """Produce the text for the default help.

        - global_options: options defined at charmcraft level (not in the commands),
          with the (options, description) structure

        The help text has the following structure:

        - usage
        - summary
        - common commands listed and described shortly
        - all commands grouped, just listed
        - more help
        """
        textblocks = []

        # title
        textblocks.append(HEADER.format(appname=self.appname))

        # summary
        textblocks.append("Summary:" + textwrap.indent(self.general_summary, "    "))

        # column alignment is dictated by longest common commands names and groups names
        max_title_len = 0

        # collect common commands
        common_commands = []
        for command_group in self.command_groups:
            max_title_len = max(len(command_group.name), max_title_len)
            for cmd in command_group.commands:
                if cmd.common:
                    common_commands.append(cmd)
                    max_title_len = max(len(cmd.name), max_title_len)

        for title, _ in global_options:
            max_title_len = max(len(title), max_title_len)

        global_lines = ["Global options:"]
        for title, text in global_options:
            global_lines.extend(_build_item(title, text, max_title_len))
        textblocks.append("\n".join(global_lines))

        common_lines = ["Starter commands:"]
        for cmd in sorted(common_commands, key=attrgetter("name")):
            common_lines.extend(_build_item(cmd.name, cmd.help_msg, max_title_len))
        textblocks.append("\n".join(common_lines))

        grouped_lines = ["Commands can be classified as follows:"]
        for command_group in sorted(self.command_groups, key=attrgetter("name")):
            command_names = ", ".join(sorted(cmd.name for cmd in command_group.commands))
            grouped_lines.extend(_build_item(command_group.name, command_names, max_title_len))
        textblocks.append("\n".join(grouped_lines))

        textblocks.append(
            textwrap.dedent(
                """
            For more information about a command, run 'charmcraft help <command>'.
            For a summary of all commands, run 'charmcraft help --all'.
        """
            )
        )

        # join all stripped blocks, leaving ONE empty blank line between
        text = "\n\n".join(block.strip() for block in textblocks) + "\n"
        return text

    def get_detailed_help(self, global_options):
        """Produce the text for the detailed help.

        - global_options: options defined at charmcraft level (not in the commands),
          with the (options, description) structure

        The help text has the following structure:

        - usage
        - summary
        - global options
        - all commands shown with description, grouped
        - more help
        """
        textblocks = []

        # title
        textblocks.append(HEADER.format(appname=self.appname))

        # summary
        textblocks.append("Summary:" + textwrap.indent(self.general_summary, "    "))

        # column alignment is dictated by longest common commands names and groups names
        max_title_len = 0
        for command_group in self.command_groups:
            for cmd in command_group.commands:
                max_title_len = max(len(cmd.name), max_title_len)
        for title, _ in global_options:
            max_title_len = max(len(title), max_title_len)

        global_lines = ["Global options:"]
        for title, text in global_options:
            global_lines.extend(_build_item(title, text, max_title_len))
        textblocks.append("\n".join(global_lines))

        textblocks.append("Commands can be classified as follows:")

        for command_group in self.command_groups:
            group_lines = ["{}:".format(command_group.name)]
            for cmd in command_group.commands:
                group_lines.extend(_build_item(cmd.name, cmd.help_msg, max_title_len))
            textblocks.append("\n".join(group_lines))

        textblocks.append(
            textwrap.dedent(
                """
            For more information about a specific command, run 'charmcraft help <command>'.
        """
            )
        )

        # join all stripped blocks, leaving ONE empty blank line between
        text = "\n\n".join(block.strip() for block in textblocks) + "\n"
        return text

    def get_command_help(self, command, arguments):
        """Produce the text for each command's help.

        - command: the instantiated command for which help is prepared

        - arguments: all command options and parameters, with the (name, description) structure

        The help text has the following structure:

        - usage
        - summary
        - options
        - other related commands
        - footer
        """
        textblocks = []

        # separate all arguments into the parameters and optional ones, just checking
        # if first char is a dash
        parameters = []
        options = []
        for name, title in arguments:
            if name[0] == "-":
                options.append((name, title))
            else:
                parameters.append(name)

        textblocks.append(
            textwrap.dedent(
                """\
            Usage:
                charmcraft {} [options] {}
        """.format(
                    command.name,
                    " ".join("<{}>".format(parameter) for parameter in parameters),
                )
            )
        )

        textblocks.append("Summary:{}".format(textwrap.indent(command.overview, "    ")))

        # column alignment is dictated by longest options title
        max_title_len = max(len(title) for title, text in options)

        # command options
        option_lines = ["Options:"]
        for title, text in options:
            option_lines.extend(_build_item(title, text, max_title_len))
        textblocks.append("\n".join(option_lines))

        # recommend other commands of the same group
        for command_group in self.command_groups:
            if any(isinstance(command, command_class) for command_class in command_group.commands):
                break
        else:
            raise RuntimeError("Internal inconsistency in commands groups")
        other_command_names = [
            c.name for c in command_group.commands if not isinstance(command, c)
        ]
        if other_command_names:
            see_also_block = ["See also:"]
            see_also_block.extend(("    " + name) for name in sorted(other_command_names))
            textblocks.append("\n".join(see_also_block))

        # footer
        textblocks.append(
            """
            For a summary of all commands, run 'charmcraft help --all'.
        """
        )

        # join all stripped blocks, leaving ONE empty blank line between
        text = "\n\n".join(block.strip() for block in textblocks) + "\n"
        return text


help_builder = HelpBuilder()
