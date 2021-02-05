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

"""Infrastructure for common base commands functionality."""


class CommandError(Exception):
    """Base exception for all error commands.

    It optionally receives a `retcode` parameter that will be the returned code
    by the process on exit, and a `argsparsing` one to indicate that the problem
    is in the command line usage.

    XXX Facundo 2020-09-21: This will be refactored soon in the branch where all
    output messages are standarized.
    """

    def __init__(self, message, retcode=1, argsparsing=False):
        self.retcode = retcode
        self.argsparsing = argsparsing
        super().__init__(message)


class BaseCommand:
    """Base class to build charmcraft commands.

    Subclass this to create a new command; the subclass must define the following attributes:

    - name: the identifier in the command line
    - help_msg: a one line help for user documentation
    - common: if it's a common/starter command, which are prioritized in the help
    - needs_config: will ensure a config is provided when executing the command

    It also must/can override some methods for the proper command behaviour (see each
    method's docstring).

    The subclass must be declared in the corresponding section of main.COMMAND_GROUPS,
    and will receive and store this group on instantiation (if overriding `__init__`, the
    subclass must pass it through upwards).
    """

    name = None
    help_msg = None
    overview = None
    common = False
    needs_config = False

    def __init__(self, group, config):
        self.group = group
        self.config = config

    def fill_parser(self, parser):
        """Specify command's specific parameters.

        Each command parameters are independant of other commands, but note there are some
        global ones (see `main.Dispatcher._build_argument_parser`).

        If this method is not overriden, the command will not have any parameters.
        """

    def run(self, parsed_args):
        """Execute command's actual functionality.

        It must be overridden by the command implementation.

        This will receive parsed arguments that were defined in :meth:.fill_parser.
        """
        raise NotImplementedError()
