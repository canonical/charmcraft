# Copyright 2021-2022 Canonical Ltd.
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
import pathlib
from abc import ABC, abstractmethod
from typing import Generator, Tuple, Union

from craft_cli import emit, CraftError
from craft_providers import Executor, ProviderError

from charmcraft.config import Base
from charmcraft.utils import get_host_architecture
from .providers import BASE_CHANNEL_TO_PROVIDER_BASE


class Provider(ABC):
    """Charmcraft's build environment provider."""

    def clean_project_environments(self, *, instance_name: str) -> None:
        """Clean up any environments created for project.

        :param instance_name: name of the instance to clean

        :raises CraftError: If environment cannot be deleted.
        """
        if not self.is_provider_installed():
            emit.debug("Not cleaning environment because the provider is not installed.")
            return

        environment = self.environment(instance_name=instance_name)
        try:
            if environment.exists():
                environment.delete()
        except ProviderError as error:
            raise CraftError(str(error)) from error

    @classmethod
    @abstractmethod
    def ensure_provider_is_available(cls) -> None:
        """Ensure provider is available, prompting the user to install it if required.

        :raises CraftError: if provider is not available.
        """

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

        if base.channel not in BASE_CHANNEL_TO_PROVIDER_BASE:
            *firsts, last = sorted(BASE_CHANNEL_TO_PROVIDER_BASE)
            allowed = f"{', '.join(map(repr, firsts))} or {last!r}"
            return (
                False,
                f"channel {base.channel!r} is not yet supported (must be {allowed})",
            )

        return True, None

    @classmethod
    @abstractmethod
    def is_provider_installed(cls) -> bool:
        """Check if provider is installed.

        :returns: True if installed.
        """

    @abstractmethod
    def environment(self, *, instance_name: str) -> Executor:
        """Create a bare environment for specified base.

        No initializing, launching, or cleaning up of the environment occurs.

        :param instance_name: Name of the instance.
        """

    @abstractmethod
    @contextlib.contextmanager
    def launched_environment(
        self,
        *,
        charm_name: str,
        project_path: pathlib.Path,
        base_configuration: Base,
        build_base: str,
        instance_name: str,
    ) -> Generator[Executor, None, None]:
        """Configure and launch environment for specified base.

        :param charm_name: Name of project.
        :param project_path: Path to project.
        :param base_configuration: Base configuration to apply to instance.
        :param build_base: Base to build from.
        :param instance_name: Name of the instance to launch.
        """
