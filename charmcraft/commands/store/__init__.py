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
    help_msg = "Login to Ubuntu Single Sign On."

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Login successful")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "Clear session credentials."

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Credentials cleared")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "Returns your login information relevant to the Store."

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


class RegisterNameCommand(BaseCommand):
    """Register a name in the Store."""
    name = 'register'
    help_msg = "Register a name in the Store."

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="the name to register in the Store")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("Congrats! You are now the publisher of %r", parsed_args.name)


class ListRegisteredCommand(BaseCommand):
    """List the charms registered in the Store."""
    name = 'list'
    help_msg = "List the charms registered the Store."

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
            data.append([
                item.name,
                visibility,
                item.status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)
