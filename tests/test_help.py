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

import pytest

from charmcraft.main import COMMAND_GROUPS


# -- verifications on different help texts

all_commands = list.__add__(*[commands for _, _, commands in COMMAND_GROUPS])


@pytest.mark.parametrize('command', all_commands)
def test_aesthetic_help_msg(command):
    """All the real commands help msg start with uppercase and ends with a dot."""
    msg = command.help_msg
    assert msg[0].isupper() and msg[-1] == '.'


@pytest.mark.parametrize('command', all_commands)
def test_aesthetic_args_options_msg(command):
    """All the real commands args/options help messages start and end with a dot."""
    class FakeParser:
        """A fake to get the arguments added."""

        def add_argument(self, *args, **kwargs):
            help_msg = kwargs.get('help')
            assert help_msg, "The help message must be present in each option"
            assert help_msg[0].isupper() and help_msg[-1] == '.'

    command('group').fill_parser(FakeParser())
