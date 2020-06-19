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

"""A client to hit the Store."""

import logging
import os
from http.cookiejar import MozillaCookieJar

from macaroonbakery import httpbakery

from charmcraft.cmdbase import CommandError

logger = logging.getLogger(__name__)


# XXX Facundo 2020-06-19: put this in the user's config directory, with proper permissions, if
# we finally decide to save credentials to a file
COOKIE_JAR_FILE = '.charmcraft_credentials'

# XXX Facundo 2020-06-19: only staging for now; will make it "multi-server" when we have proper
# functionality in Store's production
BASE_URL = 'https://api.staging.snapcraft.io/publisher/api'


class _AuthHolder:
    """Holder and wrapper of all authentication bits.

    Main two purposes of this class:

    - deal with credentials persistence

    - wrap HTTP calls to ensure authentication

    XXX Facundo 2020-06-18: right now for functionality bootstrapping we're storing credentials
    on disk, we may move to a keyring, wallet, other solution, or firmly remain here when we
    get a "security" recommendation.
    """

    def __init__(self):
        self._client = None

    def _load_credentials(self):
        self._client = httpbakery.Client(cookies=MozillaCookieJar(COOKIE_JAR_FILE))

        if os.path.exists(COOKIE_JAR_FILE):
            logger.debug("Loading credentials from file: %r", COOKIE_JAR_FILE)
            try:
                self._client.cookies.load()
            except Exception as err:
                # alert and continue processing (without having credentials, of course, the user
                # will be asked to authenticate
                logger.warning("Failed to read credentials: %r", err)
        else:
            logger.debug("Credentials file not found: %r", COOKIE_JAR_FILE)

        # iterates the cookiejar (which is mutable, may change later) and get the cookies
        # for comparison after hitting the endpoint
        self._old_cookies = list(self._client.cookies)

    def request(self, method, url):
        """Do a request."""
        if self._client is None:
            # load everything on first usage
            self._load_credentials()

        # this request through the bakery lib will automatically catch any authentication
        # problem and (if any) ask the user to authenticate and retry the original request
        # XXX Facundo 2020-06-19: this will dirty our stdout, we would need to capture it
        # and properly log it; related:
        # https://github.com/go-macaroon-bakery/py-macaroon-bakery/issues/85
        resp = self._client.request(method, url)

        if list(self._client.cookies) != self._old_cookies:
            logger.debug("Saving credentials to file: %r", COOKIE_JAR_FILE)
            self._client.cookies.save()

        return resp


class Client:
    def __init__(self):
        self._auth_client = _AuthHolder()

    def _hit(self, method, urlpath):
        """Generic hit to the Store."""
        url = BASE_URL + urlpath
        logger.debug("Hitting the store: %s %s", method, url)
        resp = self._auth_client.request(method, url)
        if not resp.ok:
            raise CommandError(
                "Failure working with the Store: [{}] {}".format(resp.status_code, resp.content))

        data = resp.json()
        return data

    def get(self, urlpath):
        """GET something from the Store."""
        return self._hit('GET', urlpath)
