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

# the summary of the whole program, already indented so it represents the real
# "columns spread", for easier human editing.
SUMMARY = """
    Charmcraft provides a streamlined, powerful, opinionated and
    flexible tool to develop, package and manage the lifecycle of
    Juju charm publication, focused particularly on charms written
    within the Operator Framework.
"""
# XXX Facundo 2020-07-13: we should add an extra (separated) line to the summary with:
#   See <url> for additional documentation.

# generic intro and outro texts
HEADER = """
Usage:
    charmcraft [help] <command>
"""
FOOTER = """
For more information about a command, run 'charmcraft help <command>'.
For a summary of all commands, run 'charmcraft help --all'.
"""

USAGE = """\
Usage: charmcraft [OPTIONS] COMMAND [ARGS]...
Try '{fullcommand} -h' for help.

Error: {error_message}
"""


def get_error_message(fullcommand, error_message):  # FIXME: missing tests!!
    """Build a usage and error message."""
    return USAGE.format(fullcommand=fullcommand, error_message=error_message)


def _build_item(title, text, title_space):
    """Show an item in the help, generically a title and a text aligned.

    The title starts in column 4 with an extra ':'. The text starts in
    4 plus the title space; if too wide it's wrapped.
    """
    text_space = TERMINAL_WIDTH - title_space - 4
    wrapped_lines = textwrap.wrap(text, text_space)

    # first line goes with the title at column 4
    title += ':'
    result = ["    {:<{title_space}s}{}".format(title, wrapped_lines[0], title_space=title_space)]

    # the rest (if any) still aligned but without title
    for line in wrapped_lines[1:]:
        result.append(" " * (title_space + 4) + line)

    return result


def get_full_help(command_groups, global_options):
    """Produce the text for the default help.

    The default help has the following structure:

    - usage
    - summary (link to docs)
    - common commands listed and described shortly
    - all commands grouped and listed
    - more help
    """
    textblocks = []

    # title
    textblocks.append(HEADER)

    # summary
    textblocks.append("Summary:" + SUMMARY)

    # column alignment is dictated by longest common commands names and groups names
    max_title_len = 0

    # collect common commands
    common_commands = []
    for group, _, commands in command_groups:
        max_title_len = max(len(group), max_title_len)
        for cmd in commands:
            if cmd.common:
                common_commands.append(cmd)
                max_title_len = max(len(cmd.name), max_title_len)

    for title, _ in global_options:
        max_title_len = max(len(title), max_title_len)

    # leave two spaces after longest title (also considering the ':')
    max_title_len += 3

    global_lines = ["Global options:"]
    for title, text in global_options:
        global_lines.extend(_build_item(title, text, max_title_len))
    textblocks.append("\n".join(global_lines))

    common_lines = ["Starter commands:"]
    for cmd in sorted(common_commands, key=attrgetter('name')):
        common_lines.extend(_build_item(cmd.name, cmd.help_msg, max_title_len))
    textblocks.append("\n".join(common_lines))

    grouped_lines = ["Commands can be classified as follows:"]
    for group, _, commands in sorted(command_groups):
        command_names = ", ".join(sorted(cmd.name for cmd in commands))
        grouped_lines.extend(_build_item(group, command_names, max_title_len))
    textblocks.append("\n".join(grouped_lines))

    textblocks.append(FOOTER)

    # join all stripped blocks, leaving ONE empty blank line between
    text = '\n\n'.join(block.strip() for block in textblocks) + '\n'
    return text


def get_command_help(command, options):
    """Produce the text for each command's help.

    It has the following structure:

    - usage
    - summary (link to docs)
    - command options
    - related commands
    - footer
    """
    # FIXME: implement!! the following is just a mockup, to prove we have all the info

    textblocks = []

    textblocks.append("""
    Usage:
        charmcraft {} [options] ?????
    """.format(command.name))
    # FIXME: this structure is complicated! we could use parser.format_usage(), examples:
    #   'usage: charmcraft register [-h] [-v | -q] name\n'
    #   'usage: charmcraft build [-h] [-v | -q] [-f FROM] [-e ENTRYPOINT] [-r REQUIREMENT]\n'

    textblocks.append("""
    Summary:
        FIXME: we need a summary in each command!!!
    """)  # FIXME

    # column alignment is dictated by longest options title (plus ':' and two intercolumn spaces)
    max_title_len = max(len(title) for title, text in options) + 3

    # command options
    option_lines = ["Command options:"]
    for title, text in options:
        option_lines.extend(_build_item(title, text, max_title_len))
    textblocks.append("\n".join(option_lines))

    # FIXME: "see also"!! (put commands of the same group?)

    # footer
    textblocks.append("""
    For a summary of all commands, run 'charmcraft help --all'.
    """)

    # join all stripped blocks, leaving ONE empty blank line between
    text = '\n\n'.join(block.strip() for block in textblocks) + '\n'
    return text

# $juju help deploy
#
# Usage:
#     juju deploy [options] <charm or bundle> [<application name>]
#
# Summary:
#     Deploy a new application or bundle.
#     <charm or bundle> can be a charm/bundle URL, or an unambiguously condensed
#     form of it; assuming a current series of "trusty", the following forms will     be accepted:
#
#     link to docs!!
#
# Command options:
#              --constraints=            Set application constraints
#
#              --dry-run=[false]        Just show what the bundle deploy would do
#             --force=[false]            Allow a charm to be deployed to a machine
#                                 running an unsupported series
#              --increase-budget=[0…]     increase model budget allocation by this
#                                 amount
#          -m,     --model=                 Model to operate in. Accepts
#                                 [<controller name>:]<model name>
#              --map-machines=            Specify the existing machines to use for
#                                 bundle deployments
#          -n,     --num-units=[1…]        Number of application units to deploy for
#                                 principal charms
#              --overlay=                 Bundles to overlay on the primary bundle,
#                                 applied in order
#              --plan=                 Plan to deploy charm under
#              --resource=                 Resource to be uploaded to the controller
#              --series=                 The series on which to deploy
#              --storage=                 Charm storage constraints
#              --to=                The machine and/or container to deploy the
#                                 unit in (bypasses constraints)
#              --trust=[false]            Allows charm to run hooks that require
#                                 access credentials
#
# See also:
#      add-unit
#      config
#      set-constraints
#      get-constraints
#      spaces
#
#
# For a summary of all commands, run 'juju help --all'.
