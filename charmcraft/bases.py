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

"""Logic dealing with bases."""

import logging
from typing import Tuple, Union

from charmcraft.config import Base
from charmcraft.utils import get_host_architecture, get_os_platform

logger = logging.getLogger(__name__)


def get_host_as_base() -> Base:
    """Get host OS represented as Base.

    The host OS name is translated to lower-case for consistency.

    :returns: Base configuration matching host.
    """
    os_platform = get_os_platform()
    host_arch = get_host_architecture()
    name = os_platform.system.lower()
    channel = os_platform.release

    return Base(name=name, channel=channel, architectures=[host_arch])


def check_if_base_matches_host(base: Base) -> Tuple[bool, Union[str, None]]:
    """Check if given base matches the host.

    :param base: Base to check.

    :returns: Tuple of bool indicating whether it is a match, with optional
              reason if not a match.
    """
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]

    if host_base.name != base.name:
        return False, f"name {base.name!r} does not match host {host_base.name!r}"

    if host_base.channel != base.channel:
        return (
            False,
            f"channel {base.channel!r} does not match host {host_base.channel!r}",
        )

    if host_arch not in base.architectures:
        return (
            False,
            f"host architecture {host_arch!r} not in base architectures {base.architectures!r}",
        )

    return True, None
