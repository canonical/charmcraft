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

from charmcraft.cmdbase import CommandError, BaseCommand
from charmcraft.main import COMMAND_GROUPS


def test_commanderror_retcode_default():
    """The CommandError return code default."""
    err = CommandError('problem')
    assert err.retcode == 1


def test_commanderror_retcode_given():
    """The CommandError holds the return code."""
    err = CommandError('problem', retcode=4)
    assert err.retcode == 4


all_commands = list.__add__(*[commands for _, _, commands in COMMAND_GROUPS])


@pytest.mark.parametrize('command', all_commands)
@pytest.mark.parametrize('attrib', ['name', 'help_msg', 'overview'])
def test_basecommand_mandatory_attributes(command, attrib):
    """All commands must provide the mandatory attributes."""
    assert getattr(command, attrib) is not None


def test_basecommand_holds_the_indicated_info():
    """BaseCommand subclasses ."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

    group = 'test group'
    config = 'test config'
    tc = TestClass(group, config)
    assert tc.group == group
    assert tc.config == config


def test_basecommand_fill_parser_optional():
    """BaseCommand subclasses are allowed to not override fill_parser."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

        def __init__(self, group, config):
            self.done = False
            super().__init__(group, config)

        def run(self, parsed_args):
            self.done = True

    tc = TestClass('group', 'config')
    tc.run([])
    assert tc.done


def test_basecommand_run_mandatory():
    """BaseCommand subclasses must override run."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

    tc = TestClass('group', 'config')
    with pytest.raises(NotImplementedError):
        tc.run([])
