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

"""Tests for the commands infraestructure."""

import pytest

from charmcraft.cmdbase import CommandError
from charmcraft.main import COMMAND_GROUPS


def test_commanderror_retcode_default():
    """The CommandError return code default."""
    err = CommandError("problem")
    assert err.retcode == 1


def test_commanderror_retcode_given():
    """The CommandError holds the return code."""
    err = CommandError("problem", retcode=4)
    assert err.retcode == 4


all_commands = list.__add__(*[cgroup.commands for cgroup in COMMAND_GROUPS])


@pytest.mark.parametrize("command", all_commands)
@pytest.mark.parametrize("attrib", ["name", "help_msg", "overview"])
def test_basecommand_mandatory_attributes(command, attrib):
    """All commands must provide the mandatory attributes."""
    fixme # solucionar de otra manera
    assert getattr(command, attrib) is not None


# -- tests for strings in commands


@pytest.mark.parametrize("command", all_commands)
def test_aesthetic_help_msg(command):
    """All real commands help msgs start with uppercase and do not end with a dot."""
    fixme # mover a main
    msg = command.help_msg
    assert msg[0].isupper() and msg[-1] != "."


@pytest.mark.parametrize("command", all_commands)
def test_aesthetic_args_options_msg(command, config):
    """All real commands args help messages start with uppercase and do not end with a dot."""
    fixme # mover a main

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
