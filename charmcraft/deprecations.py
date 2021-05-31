# Copyright 2021 Canonical Ltd.
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

"""Handle surfacing deprecation notices.

When a new deprecation has occurred, write a Deprecation Notice for it here
(assigning it the next DN<nn> ID):

    https://discourse.charmhub.io/t/4652

Then add that ID along with the deprecation title in the list below.
"""

import logging

logger = logging.getLogger(__name__)


_DEPRECATION_MESSAGES = {
    "dn01": "Configuration keywords are now separated using dashes.",
}

_DEPRECATION_URL_FMT = "https://discourse.charmhub.io/t/4652#heading--{deprecation_id}"


def notify_deprecation(deprecation_id):
    """Present proper messages to the user for the indicated deprecation id."""
    message = _DEPRECATION_MESSAGES[deprecation_id]
    logger.warning("DEPRECATED: %s", message)
    url = _DEPRECATION_URL_FMT.format(deprecation_id=deprecation_id)
    logger.warning("See %s for more information.", url)
