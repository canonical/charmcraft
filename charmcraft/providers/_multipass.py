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
from typing import Generator

from craft_cli import CraftError
from craft_providers import bases, multipass, Executor
from craft_providers.multipass.errors import MultipassError

from charmcraft.config import Base

from ._provider import Provider


PROVIDER_BASE_TO_MULTIPASS_BASE = {
    bases.BuilddBaseAlias.BIONIC.value: "snapcraft:18.04",
    bases.BuilddBaseAlias.FOCAL.value: "snapcraft:20.04",
    bases.BuilddBaseAlias.JAMMY.value: "snapcraft:22.04",
}


class MultipassProvider(Provider):
    """Charmcraft's build environment provider.

    :param multipass: Optional Multipass client to use.
    """

    name = "Multipass"
    install_recommendation = (
        "Visit https://multipass.run/ "
        "for instructions on installing Multipass for your operating system."
    )

    def __init__(
        self,
        *,
        multipass: multipass.Multipass = multipass.Multipass(),
    ) -> None:
        self.multipass = multipass

    @classmethod
    def ensure_provider_is_available(cls) -> None:
        """Ensure provider is available and ready, installing if required.

        :raises CraftError: if provider is not available.
        """
        if not multipass.is_installed():
            try:
                multipass.install()
            except multipass.MultipassInstallationError as error:
                raise CraftError(
                    f"Failed to install Multipass. {cls.install_recommendation}"
                ) from error

        try:
            multipass.ensure_multipass_is_ready()
        except multipass.MultipassError as error:
            raise CraftError(str(error)) from error

    @classmethod
    def is_provider_installed(cls) -> bool:
        """Check if provider is installed.

        :returns: True if installed.
        """
        return multipass.is_installed()

    def environment(self, *, instance_name: str) -> Executor:
        """Create a bare environment for specified base.

        No initializing, launching, or cleaning up of the environment occurs.

        :param instance_name: Name of the instance.
        """
        return multipass.MultipassInstance(name=instance_name)

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
        try:
            instance = multipass.launch(
                name=instance_name,
                base_configuration=base_configuration,
                image_name=PROVIDER_BASE_TO_MULTIPASS_BASE[build_base],
                cpus=2,
                disk_gb=64,
                mem_gb=2,
                auto_clean=True,
            )
        except (bases.BaseConfigurationError, MultipassError) as error:
            raise CraftError(str(error)) from error

        try:
            yield instance
        finally:
            # Ensure to unmount everything and stop instance upon completion.
            try:
                instance.unmount_all()
                instance.stop()
            except MultipassError as error:
                raise CraftError(str(error)) from error
