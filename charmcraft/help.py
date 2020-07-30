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
    Charmcraft provides a streamlined, powerful, opinionated, and
    flexible tool to develop, package, and manage the lifecycle of
    Juju charm publication, focused particularly on charms written
    within the Operator Framework.
"""
# XXX Facundo 2020-07-13: we should add an extra (separated) line to the summary with:
#   See <url> for additional documentation.


#FIXME: help command!
#FIXME: help --all


def _build_item(title, text, title_space):
    """Show an item in the help, generically a title and a text aligned.

    The title starts in column 4 with an extra ':'. The text starts in
    4 plus the title space; if too wide it's wrapped.
    """
    print("======== build", (title, text, title_space))
    text_space = TERMINAL_WIDTH - title_space - 4
    wrapped_lines = textwrap.wrap(text, text_space)
    print("====== wrapped", wrapped_lines)

    # first line goes with the title at column 4
    title += ':'
    result = ["    {:<{title_space}s}{}".format(title, wrapped_lines[0], title_space=title_space)]

    # the rest (if any) still aligned but without title
    for line in wrapped_lines[1:]:
        result.append(" " * (title_space + 4) + line)

    print("====== result", result)
    return result


def get_full_help(command_groups):
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
    textblocks.append(textwrap.dedent("""\
        Usage:
            charmcraft [help] <command>
    """))

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
                print("====== cmd", cmd.name, cmd.common)
                common_commands.append(cmd)
                max_title_len = max(len(cmd.name), max_title_len)

    print("====== max len", max_title_len)
    # leave two spaces between longest title (also considering the ':')
    max_title_len += 3

    common_lines = ["Starter commands:"]
    for cmd in sorted(common_commands, key=attrgetter('name')):
        common_lines.extend(_build_item(cmd.name, cmd.help_msg, max_title_len))
    textblocks.append("\n".join(common_lines))  #FIXME: maybe one join at the end?






    # join all stripped blocks, leaving ONE empty blank line
    text = '\n\n'.join(block.strip() for block in textblocks) + '\n'
    return text
