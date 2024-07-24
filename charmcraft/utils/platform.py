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
"""Platform-related Charmcraft utilities."""
import dataclasses
import pathlib
import platform
from collections.abc import Iterable

import distro
from craft_application import errors
from craft_parts.utils.formatting_utils import humanize_list

from charmcraft import const


@dataclasses.dataclass(frozen=True)
class OSPlatform:
    """Description of an operating system platform."""

    system: str
    release: str
    machine: str


def get_os_platform(filepath: pathlib.Path = pathlib.Path("/etc/os-release")) -> OSPlatform:
    """Determine a system/release combo for an OS using /etc/os-release if available."""
    system = platform.system()
    release = platform.release()
    machine = platform.machine()

    if system == "Linux":
        info = distro.info()
        system = info.get("id", system)
        # Treat Ubuntu derivatives as Ubuntu, as they should be compatible.
        if system != "ubuntu" and "ubuntu" in info.get("like", "").split():
            system = "ubuntu"
        release = info.get("version", release)

    return OSPlatform(system=system, release=release, machine=machine)


def validate_architectures(architectures: Iterable[str], *, allow_all: bool = False) -> None:
    """Validate that all architectures provided are valid architecture names."""
    architectures = set(architectures)
    if allow_all and "all" in architectures:
        if architectures == {"all"}:
            return
        raise errors.CraftValidationError(
            "If 'all' is defined for architectures, it must be the only architecture."
        )
    invalid = architectures - const.SUPPORTED_ARCHITECTURES
    if invalid:
        raise errors.CraftValidationError(
            f"Invalid architecture(s): {', '.join(invalid)}",
            details=f"Valid architecture values are: {humanize_list(sorted(const.SUPPORTED_ARCHITECTURES), 'and')}",
        )
