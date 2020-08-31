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

import logging
import time
from collections import namedtuple

from dateutil import parser

from charmcraft.commands.store.client import Client

logger = logging.getLogger('charmcraft.commands.store')

# helpers to build responses from this layer
User = namedtuple('User', 'name username userid')
Charm = namedtuple('Charm', 'name private status')
Uploaded = namedtuple('Uploaded', 'ok status revision')
# XXX Facundo 2020-07-23: Need to do a massive rename to call `revno` to the "revision as
# the number" inside the "revision as the structure", this gets super confusing in the code with
# time, and now it's the moment to do it (also in Release below!)
Revision = namedtuple('Revision', 'revision version created_at status errors')
Error = namedtuple('Error', 'message code')
Release = namedtuple('Release', 'revision channel expires_at')
Channel = namedtuple('Channel', 'name fallback track risk branch')

# those statuses after upload that flag that the review ended (and if it ended succesfully or not)
UPLOAD_ENDING_STATUSES = {
    'approved': True,
    'rejected': False,
}
POLL_DELAY = 1


def _build_revision(item):
    """Build a Revision from a response item."""
    errors = [Error(message=e['message'], code=e['code']) for e in (item['errors'] or [])]
    rev = Revision(
        revision=item['revision'],
        version=item['version'],
        created_at=parser.parse(item['created-at']),
        status=item['status'],
        errors=errors,
    )
    return rev


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
        for item in response['results']:
            result.append(Charm(name=item['name'], private=item['private'], status=item['status']))
        return result

    def upload(self, name, filepath):
        """Upload the content of filepath to the indicated charm."""
        upload_id = self._client.push(filepath)

        endpoint = '/v1/charm/{}/revisions'.format(name)
        response = self._client.post(endpoint, {'upload-id': upload_id})
        status_url = response['status-url']
        logger.debug("Upload %s started, got status url %s", upload_id, status_url)

        while True:
            response = self._client.get(status_url)
            logger.debug("Status checked: %s", response)

            # as we're asking for a single upload_id, the response will always have only one item
            (revision,) = response['revisions']
            status = revision['status']

            if status in UPLOAD_ENDING_STATUSES:
                return Uploaded(
                    ok=UPLOAD_ENDING_STATUSES[status],
                    status=status, revision=revision['revision'])

            # XXX Facundo 2020-06-30: Implement a slight backoff algorithm and fallout after
            # N attempts (which should be big, as per snapcraft experience). Issue: #79.
            time.sleep(POLL_DELAY)

    def list_revisions(self, name):
        """Return charm revisions for the indicated charm."""
        response = self._client.get('/v1/charm/{}/revisions'.format(name))
        result = [_build_revision(item) for item in response['revisions']]
        return result

    def release(self, name, revision, channels):
        """Release one or more revisions for a package."""
        endpoint = '/v1/charm/{}/releases'.format(name)
        items = [{'revision': revision, 'channel': channel} for channel in channels]
        self._client.post(endpoint, items)

    def list_releases(self, name):
        """List current releases for a package."""
        endpoint = '/v1/charm/{}/releases'.format(name)
        response = self._client.get(endpoint)

        channel_map = []
        for item in response['channel-map']:
            expires_at = item['expiration-date']
            if expires_at is not None:
                # `datetime.datetime.fromisoformat` is available only since Py3.7
                expires_at = parser.parse(expires_at)
            channel_map.append(
                Release(revision=item['revision'], channel=item['channel'], expires_at=expires_at))

        channels = [
            Channel(
                name=item['name'],
                fallback=item['fallback'],
                track=item['track'],
                risk=item['risk'],
                branch=item['branch'],
            ) for item in response['package']['channels']]

        revisions = [_build_revision(item) for item in response['revisions']]

        return channel_map, channels, revisions
