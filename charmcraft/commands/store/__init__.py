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

"""Commands related to the Store, a thin layer above real functionality."""

import logging

from tabulate import tabulate

from charmcraft.cmdbase import BaseCommand

from .store import Store

logger = logging.getLogger('charmcraft.commands.store')


class LoginCommand(BaseCommand):
    """Log into the store."""
    name = 'login'
    help_msg = "login to Ubuntu Single Sign On"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Login successful")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "clear session credentials"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Credentials cleared")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "returns your login information relevant to the store"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.whoami()

        data = [
            ('name:', result.name),
            ('username:', result.username),
            ('id:', result.userid),
        ]
        table = tabulate(data, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)
