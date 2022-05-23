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

"""Build environment provider support for charmcraft."""

import contextlib
import os
import pathlib
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Union

from craft_providers import bases

from charmcraft.config import Base
from charmcraft.utils import get_host_architecture
from ._buildd import BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS


class Provider(ABC):
    """Charmcraft's build environment provider."""

    @abstractmethod
    def clean_project_environments(
        self,
        *,
        charm_name: str,
        project_path: pathlib.Path,
    ) -> List[str]:
        """Clean up any environments created for project.

        :param charm_name: Name of project.
        :param project_path: Directory of charm project.

        :returns: List of containers deleted.
        """

    @classmethod
    @abstractmethod
    def ensure_provider_is_available(cls) -> None:
        """Ensure provider is available, prompting the user to install it if required.

        :raises CraftError: if provider is not available.
        """

    def get_command_environment(self) -> Dict[str, str]:
        """Construct the required environment."""
        env = bases.buildd.default_command_environment()
        env["CHARMCRAFT_MANAGED_MODE"] = "1"

        # Pass-through host environment that target may need.
        for env_key in ["http_proxy", "https_proxy", "no_proxy"]:
            if env_key in os.environ:
                env[env_key] = os.environ[env_key]

        return env

    def get_instance_name(
        self,
        *,
        bases_index: int,
        build_on_index: int,
        project_name: str,
        project_path: pathlib.Path,
        target_arch: str,
    ) -> str:
        """Formulate the name for an instance using each of the given parameters.

        Incorporate each of the parameters into the name to come up with a
        predictable naming schema that avoids name collisions across multiple,
        potentially complex, projects.

        :param bases_index: Index of `bases:` entry.
        :param build_on_index: Index of `build-on` within bases entry.
        :param project_name: Name of charm project.
        :param project_path: Directory of charm project.
        :param target_arch: Targeted architecture, used in the name to prevent
            collisions should future work enable multiple architectures on the same
            platform.
        """
        return "-".join(
            [
                "charmcraft",
                project_name,
                str(project_path.stat().st_ino),
                str(bases_index),
                str(build_on_index),
                target_arch,
            ]
        )

    @classmethod
    def is_base_available(cls, base: Base) -> Tuple[bool, Union[str, None]]:
        """Check if provider can provide an environment matching given base.

        :param base: Base to check.

        :returns: Tuple of bool indicating whether it is a match, with optional
                reason if not a match.
        """
        arch = get_host_architecture()
        if arch not in base.architectures:
            return (
                False,
                f"host architecture {arch!r} not in base architectures {base.architectures!r}",
            )

        if base.name != "ubuntu":
            return (
                False,
                f"name {base.name!r} is not yet supported (must be 'ubuntu')",
            )

        if base.channel not in BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS.keys():
            *firsts, last = sorted(BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS.keys())
            allowed = f"{', '.join(map(repr, firsts))} or {last!r}"
            return (
                False,
                f"channel {base.channel!r} is not yet supported (must be {allowed})",
            )

        return True, None

    @classmethod
    @abstractmethod
    def is_provider_available(cls) -> bool:
        """Check if provider is installed and available for use.

        :returns: True if installed.
        """

    @abstractmethod
    @contextlib.contextmanager
    def launched_environment(
        self,
        *,
        charm_name: str,
        project_path: pathlib.Path,
        base: Base,
        bases_index: int,
        build_on_index: int,
    ):
        """Launch environment for specified base.

        :param charm_name: Name of project.
        :param project_path: Path to project.
        :param base: Base to create.
        :param bases_index: Index of `bases:` entry.
        :param build_on_index: Index of `build-on` within bases entry.
        """
