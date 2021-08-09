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

"""Buildd-related for charmcraft."""

from typing import Optional

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS = {
    "18.04": bases.BuilddBaseAlias.BIONIC,
    "20.04": bases.BuilddBaseAlias.FOCAL,
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

            - python3 pip and setuptools installed

        :param executor: Executor for target container.
        :param retry_wait: Duration to sleep() between status checks (if
            required).
        :param timeout: Timeout in seconds.

        :raises BaseCompatibilityError: if instance is incompatible.
        :raises BaseConfigurationError: on other unexpected error.
        """
        super().setup(executor=executor, retry_wait=retry_wait, timeout=timeout)

        try:
            snap_installer.inject_from_host(
                executor=executor, snap_name="charmcraft", classic=True
            )
        except snap_installer.SnapInstallationError as error:
            raise bases.BaseConfigurationError(
                brief="Failed to inject host Charmcraft snap into target environment.",
            ) from error
