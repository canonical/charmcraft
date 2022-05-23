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

"""Buildd-related for charmcraft."""

import sys
from typing import Optional

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

from charmcraft.env import get_managed_environment_snap_channel


BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS = {
    "18.04": bases.BuilddBaseAlias.BIONIC,
    "20.04": bases.BuilddBaseAlias.FOCAL,
    "22.04": bases.BuilddBaseAlias.JAMMY,
}


class CharmcraftBuilddBaseConfiguration(bases.BuilddBase):
    """Base configuration for Charmcraft.

    :cvar compatibility_tag: Tag/Version for variant of build configuration and
        setup.  Any change to this version would indicate that prior [versioned]
        instances are incompatible and must be cleaned.  As such, any new value
        should be unique to old values (e.g. incrementing).  Charmcraft extends
        the buildd tag to include its own version indicator (.0) and namespace
        ("charmcraft").
    """

    compatibility_tag: str = f"charmcraft-{bases.BuilddBase.compatibility_tag}.0"

    def _setup_charmcraft(self, *, executor: Executor) -> None:
        """Install Charmcraft in target environment.

        On Linux, the default behavior is to inject the host snap into the target
        environment.

        On other platforms, the Charmcraft snap is installed from the Snap Store.

        When installing the snap from the Store, we check if the user specifies a
        channel, using CHARMCRAFT_INSTALL_SNAP_CHANNEL=<channel>.  If unspecified,
        we use the "stable" channel on the default track.

        On Linux, the user may specify this environment variable to force Charmcraft
        to install the snap from the Store rather than inject the host snap.

        :raises BaseConfigurationError: on error.
        """
        snap_channel = get_managed_environment_snap_channel()
        if snap_channel is None and sys.platform != "linux":
            snap_channel = "stable"

        if snap_channel:
            try:
                snap_installer.install_from_store(
                    executor=executor, snap_name="charmcraft", channel=snap_channel, classic=True
                )
            except snap_installer.SnapInstallationError as error:
                raise bases.BaseConfigurationError(
                    brief="Failed to install Charmcraft snap from store channel "
                    f"{snap_channel!r} into target environment.",
                ) from error
        else:
            try:
                snap_installer.inject_from_host(
                    executor=executor, snap_name="charmcraft", classic=True
                )
            except snap_installer.SnapInstallationError as error:
                raise bases.BaseConfigurationError(
                    brief="Failed to inject host Charmcraft snap into target environment.",
                ) from error

    def setup(
        self,
        *,
        executor: Executor,
        retry_wait: float = 0.25,
        timeout: Optional[float] = None,
    ) -> None:
        """Prepare base instance for use by the application.

        In addition to the guarantees provided by buildd:

            - charmcraft installed

        :param executor: Executor for target container.
        :param retry_wait: Duration to sleep() between status checks (if
            required).
        :param timeout: Timeout in seconds.

        :raises BaseCompatibilityError: if instance is incompatible.
        :raises BaseConfigurationError: on other unexpected error.
        """
        super().setup(executor=executor, retry_wait=retry_wait, timeout=timeout)
        self._setup_charmcraft(executor=executor)

    def warmup(
        self,
        *,
        executor: Executor,
        retry_wait: float = 0.25,
        timeout: Optional[float] = None,
    ) -> None:
        """Prepare a previously created and setup instance for use by the application.

        In addition to the guarantees provided by buildd:

            - charmcraft installed

        :param executor: Executor for target container.
        :param retry_wait: Duration to sleep() between status checks (if
            required).
        :param timeout: Timeout in seconds.

        :raises BaseCompatibilityError: if instance is incompatible.
        :raises BaseConfigurationError: on other unexpected error.
        """
        super().warmup(executor=executor, retry_wait=retry_wait, timeout=timeout)
        self._setup_charmcraft(executor=executor)
