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

import distro


@dataclasses.dataclass(frozen=True)
class OSPlatform:
    """Description of an operating system platform."""

    system: str
    release: str
    machine: str


# translations from what the platform module informs to the term deb and
# snaps actually use
ARCH_TRANSLATIONS = {
    "aarch64": "arm64",
    "armv7l": "armhf",
    "i686": "i386",
    "ppc": "powerpc",
    "ppc64le": "ppc64el",
    "x86_64": "amd64",
    "AMD64": "amd64",  # Windows support
}


def get_os_platform(filepath=pathlib.Path("/etc/os-release")):
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


def get_host_architecture():
    """Get host architecture in deb format suitable for base definition."""
    os_platform = get_os_platform()
    return ARCH_TRANSLATIONS.get(os_platform.machine, os_platform.machine)
