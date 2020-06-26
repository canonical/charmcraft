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

from charmcraft.commands.store.client import Client


class Store:
    """The main interface to the Store's API."""

    def __init__(self):
        self.client = Client()

    def register_name(self, name):
        """Register the specified name for the authenticated user."""
        resp = self.client.post('/v1/charm', {'name': name})
        return resp['charm-id']

    def list_registered_names(self):
        """Return names registered by the authenticated user."""
        resp = self.client.get('/v1/charm')
        return resp['charms']  #FIXME: consider having a hard-interface here
