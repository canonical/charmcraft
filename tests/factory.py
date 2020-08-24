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

"""Collection of creation functions for normally used objects for testing."""

from charmcraft.cmdbase import BaseCommand


def create_command(name_, help_msg_=None):
    """Helper to create commands."""
    if help_msg_ is None:
        help_msg_ = "Automatic help generated in the factory for the tests."

    class MyCommand(BaseCommand):
        name = name_
        help_msg = help_msg_

        def run(self, parsed_args):
            pass

    return MyCommand
