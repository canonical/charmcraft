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

from craft_cli import emit

from charmcraft.env import is_charmcraft_running_in_managed_mode


# the message to show for each deprecation ID (this needs to be in sync with the
# documentation)
_DEPRECATION_MESSAGES = {
    "dn03": "Bases configuration is now required.",
    "dn04": "Use 'charm-entrypoint' in charmcraft.yaml parts to define the entry point.",
    "dn05": "Use 'charm-requirements' in charmcraft.yaml parts to define requirements.",
    "dn06": "The build command is deprecated, use 'pack' instead.",
}

# the URL to point to the deprecation entry in the documentation
_DEPRECATION_URL_FMT = "https://discourse.charmhub.io/t/4652#heading--{deprecation_id}"

# already-notified deprecations will be stored here to not log them twice
_ALREADY_NOTIFIED = set()


def notify_deprecation(deprecation_id):
    """Present proper messages to the user for the indicated deprecation id.

    Prevent issuing duplicate warnings to the user by ignoring notifications if:
    - running in managed-mode
    - already issued by running process
    """
    if is_charmcraft_running_in_managed_mode() or deprecation_id in _ALREADY_NOTIFIED:
        return

    message = _DEPRECATION_MESSAGES[deprecation_id]
    emit.message(f"DEPRECATED: {message}", intermediate=True)
    url = _DEPRECATION_URL_FMT.format(deprecation_id=deprecation_id)
    emit.message(f"See {url} for more information.", intermediate=True)
    _ALREADY_NOTIFIED.add(deprecation_id)
