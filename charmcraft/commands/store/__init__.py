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

from charmcraft.cmdbase import BaseCommand
from charmcraft.commands.store.client import Client

logger = logging.getLogger(__name__)


class LoginCommand(BaseCommand):
    """Log into the store."""
    name = 'login'
    help_msg = "login in the Ubuntu Single Sign On"

    def run(self, parsed_args):
        """Run the command.

        The login happens on every request to the Store (if current credentials were not
        enough), so here we just exercise the simplest command regarding developer identity.
        """
        client = Client()
        client.clear_credentials()
        client.get('/v1/whoami')
        logger.info("Login successful")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "clear session credentials"

    def run(self, parsed_args):
        """Run the command."""
        client = Client()
        client.clear_credentials()
        logger.info("Credentials cleared.")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "returns your login information relevant to the store"

    def run(self, parsed_args):
        """Run the command."""
        client = Client()
        result = client.get('/v1/whoami')
        logger.info(
            "You are %s (username=%r, id=%r)",
            result['display-name'], result['username'], result['id'])
