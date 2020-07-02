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

"""The Store API handling."""

from collections import namedtuple

from charmcraft.commands.store.client import Client

# helper to build responses from this layer
User = namedtuple('User', 'name username userid')


class Store:
    """The main interface to the Store's API."""

    def __init__(self):
        self._client = Client()

    def login(self):
        """Login into the store.

        The login happens on every request to the Store (if current credentials were not
        enough), so to trigger a new login we...

            - remove local credentials

            - exercise the simplest command regarding developer identity
        """
        self._client.clear_credentials()
        self._client.get('/v1/whoami')

    def logout(self):
        """Logout from the store.

        There's no action really in the Store to logout, we just remove local credentials.
        """
        self._client.clear_credentials()

    def whoami(self):
        """Return authenticated user details."""
        response = self._client.get('/v1/whoami')
        result = User(
            name=response['display-name'],
            username=response['username'],
            userid=response['id'],
        )
        return result
