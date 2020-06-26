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
from charmcraft.commands.store.store import Store

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

    _titles = [
        ('name:', 'name'),
        ('username:', 'username'),
        ('id:', 'userid'),
    ]

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.whoami()

        longest_title = max(len(t[0]) for t in self._titles)
        for title, attr in self._titles:
            logger.info("%-*s %s", longest_title, title, getattr(result, attr))


class RegisterNameCommand(BaseCommand):
    """Register a name in the store."""
    name = 'register'
    help_msg = "register a name in the store"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="the name to register in the Store")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("Congrats! You are now the publisher of %r", parsed_args.name)


class ListRegisteredCommand(BaseCommand):
    """List the charms registered in the store."""
    name = 'list'
    help_msg = "list the charms registered the store"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.list_registered_names()
        if not result:
            logger.info("Nothing found")
            return

        headers = ['Name', 'Visibility', 'Status']
        data = []
        for item in result:
            visibility = 'private' if item.private else 'public'
            data.append([  # FIXME, tuple?
                item.name,
                visibility,
                item.status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain')
        for line in table.split('\n'):
            logger.info(line)
