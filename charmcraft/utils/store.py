# Copyright 2023 Canonical Ltd.
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
"""Craft store-related generic utilities."""
import enum
import functools
from dataclasses import dataclass
from typing import Optional

from craft_cli import CraftError


@functools.total_ordering
@enum.unique
class Risk(enum.Enum):
    """Standard risk tracks for a channel, orderable but not comparable to an int."""

    STABLE = 0
    CANDIDATE = 1
    BETA = 2
    EDGE = 3

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        return NotImplemented


@dataclass(frozen=True)
class ChannelData:
    """Data class for a craft store channel."""

    track: Optional[str]
    risk: Risk
    branch: Optional[str]

    @classmethod
    def from_str(cls, name: str):
        """Parse a channel name from a string using the standard store semantics.

        https://snapcraft.io/docs/channels
        """
        invalid_channel_error = CraftError(f"Invalid channel name: {name!r}")
        parts = name.split("/")
        if len(parts) == 1:
            try:
                risk = Risk[parts[0].upper()]
            except KeyError:
                raise invalid_channel_error from None
            else:
                parts = [None, risk, None]
        elif len(parts) == 2:
            try:
                risk = Risk[parts[0].upper()]
                parts.insert(0, None)
            except KeyError:
                try:
                    risk = Risk[parts[1].upper()]
                    parts.append(None)
                except KeyError:
                    raise invalid_channel_error from None
        elif len(parts) == 3:
            try:
                risk = Risk[parts[1].upper()]
            except KeyError:
                raise invalid_channel_error from None
        else:
            raise invalid_channel_error
        return cls(parts[0], risk, parts[2])

    @property
    def name(self) -> str:
        """Get the channel name as a string."""
        risk = self.risk.name.lower()
        return "/".join(i for i in (self.track, risk, self.branch) if i is not None)
