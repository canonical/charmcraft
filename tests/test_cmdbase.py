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

"""Tests for the commands infraestructure."""

import pytest

from charm.cmdbase import CommandError, BaseCommand


def test_commanderror_retcode_default():
    """The CommandError return code default."""
    err = CommandError('problem')
    assert err.retcode == -1


def test_commanderror_retcode_given():
    """The CommandError holds the return code."""
    err = CommandError('problem', retcode=-4)
    assert err.retcode == -4


def test_basecommand_mandatory_name():
    """BaseCommand subclasses must provide a name."""
    class TestClass(BaseCommand):
        help_msg = "test help"

    with pytest.raises(RuntimeError, match="Command not properly created: TestClass"):
        TestClass('group')


def test_basecommand_mandatory_helpmsg():
    """BaseCommand subclasses ."""
    class TestClass(BaseCommand):
        name = 'test'

    with pytest.raises(RuntimeError, match="Command not properly created: TestClass"):
        TestClass('group')


def test_basecommand_holds_the_indicated_group():
    """BaseCommand subclasses ."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

    group = 'test group'
    tc = TestClass(group)
    assert tc.group == group


def test_basecommand_fill_parser_optional():
    """BaseCommand subclasses are allowed to not override fill_parser."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

        def __init__(self, group):
            self.done = False
            super().__init__(group)

        def run(self, parsed_args):
            self.done = True

    tc = TestClass('group')
    tc.run([])
    assert tc.done


def test_basecommand_run_mandatory():
    """BaseCommand subclasses must override run."""
    class TestClass(BaseCommand):
        help_msg = 'help message'
        name = 'test'

    tc = TestClass('group')
    with pytest.raises(NotImplementedError):
        tc.run([])
