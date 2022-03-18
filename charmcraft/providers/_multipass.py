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
import pathlib
import re
from typing import List

from craft_cli import emit, CraftError
from craft_providers import bases, multipass
from craft_providers.multipass.errors import MultipassError

from charmcraft.config import Base
from charmcraft.env import get_managed_environment_project_path
from charmcraft.utils import confirm_with_user, get_host_architecture

from ._buildd import BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS, CharmcraftBuilddBaseConfiguration
from ._provider import Provider


class MultipassProvider(Provider):
    """Charmcraft's build environment provider.

    :param multipass: Optional Multipass client to use.
    """

    def __init__(
        self,
        *,
        multipass: multipass.Multipass = multipass.Multipass(),
    ) -> None:
        self.multipass = multipass

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
        deleted: List[str] = []

        # Nothing to do if provider is not installed.
        if not self.is_provider_available():
            return deleted

        inode = project_path.stat().st_ino

        try:
            names = self.multipass.list()
        except multipass.MultipassError as error:
            raise CraftError(str(error)) from error

        for name in names:
            match_regex = f"^charmcraft-{charm_name}-{inode}-.+-.+-.+$"
            if re.match(match_regex, name):
                emit.trace(f"Deleting Multipass VM {name!r}.")
                try:
                    self.multipass.delete(
                        instance_name=name,
                        purge=True,
                    )
                except multipass.MultipassError as error:
                    raise CraftError(str(error)) from error

                deleted.append(name)
            else:
                emit.trace(f"Not deleting Multipass VM {name!r}.")

        return deleted

    @classmethod
    def ensure_provider_is_available(cls) -> None:
        """Ensure provider is available, prompting the user to install it if required.

        :raises CraftError: if provider is not available.
        """
        if not multipass.is_installed():
            if confirm_with_user(
                "Multipass is required, but not installed. Do you wish to install Multipass "
                "and configure it with the defaults?",
                default=False,
            ):
                try:
                    multipass.install()
                except multipass.MultipassInstallationError as error:
                    raise CraftError(
                        "Failed to install Multipass. Visit https://multipass.run/ for "
                        "instructions on installing Multipass for your operating system."
                    ) from error
            else:
                raise CraftError(
                    "Multipass is required, but not installed. Visit https://multipass.run/ for "
                    "instructions on installing Multipass for your operating system."
                )

        try:
            multipass.ensure_multipass_is_ready()
        except multipass.MultipassError as error:
            raise CraftError(str(error)) from error

    @classmethod
    def is_provider_available(cls) -> bool:
        """Check if provider is installed and available for use.

        :returns: True if installed.
        """
        return multipass.is_installed()

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
        alias = BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS[base.channel]
        target_arch = get_host_architecture()

        instance_name = self.get_instance_name(
            bases_index=bases_index,
            build_on_index=build_on_index,
            project_name=charm_name,
            project_path=project_path,
            target_arch=target_arch,
        )

        environment = self.get_command_environment()
        base_configuration = CharmcraftBuilddBaseConfiguration(
            alias=alias, environment=environment, hostname=instance_name
        )

        try:
            instance = multipass.launch(
                name=instance_name,
                base_configuration=base_configuration,
                image_name=f"snapcraft:{base.channel}",
                cpus=2,
                disk_gb=64,
                mem_gb=2,
                auto_clean=True,
            )
        except (bases.BaseConfigurationError, MultipassError) as error:
            raise CraftError(str(error)) from error

        try:
            # Mount project.
            instance.mount(host_source=project_path, target=get_managed_environment_project_path())
        except MultipassError as error:
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
