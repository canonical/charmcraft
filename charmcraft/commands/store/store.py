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

# helpers to build responses from this layer
User = namedtuple('User', 'name username userid')
Charm = namedtuple('Charm', 'name private status')


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
        # XXX Facundo 2020-06-30: Every time we consume data from the Store (after a succesful
        # call) we need to wrap it with a context manager that will raise UnknownError (after
        # logging in debug the received response). This would catch API changes, for example,
        # without making charmcraft to badly crash. Related: issue #73.
        result = User(
            name=response['display-name'],
            username=response['username'],
            userid=response['id'],
        )
        return result

    def register_name(self, name):
        """Register the specified name for the authenticated user."""
        self._client.post('/v1/charm', {'name': name})

    def list_registered_names(self):
        """Return names registered by the authenticated user."""
        response = self._client.get('/v1/charm')
        result = []
        for item in response['charms']:
            result.append(Charm(name=item['name'], private=item['private'], status=item['status']))
        return result
