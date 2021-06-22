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

import logging
import subprocess
from typing import Optional

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

logger = logging.getLogger(__name__)


class CharmcraftBuilddBaseConfiguration(bases.BuilddBase):
    """Base configuration for Charmcraft.

    :cvar compatibility_tag: Tag/Version for variant of build configuration and
        setup.  Any change to this version would indicate that prior [versioned]
        instances are incompatible and must be cleaned.  As such, any new value
        should be unique to old values (e.g. incrementing).
    :cvar instance_config_path: Path to persistent environment configuration
        used for compatibility checks (or other data).  Set to
        /etc/craft-instance.conf, but may be overridden for application-specific
        reasons.
    :cvar instance_config_class: Class defining instance configuration.  May be
        overridden with an application-specific subclass of InstanceConfiguration
        to enable application-specific extensions.

    :param alias: Base alias / version.
    :param environment: Environment to set in /etc/environment.
    :param hostname: Hostname to configure.
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

        Wait for environment to become ready and configure it.  At completion of
        setup, the executor environment should have networking up and have all
        of the installed dependencies required for subsequent use by the
        application.

        Setup may be called more than once in a given instance to refresh/update
        the environment.

        If timeout is specified, abort operation if time has been exceeded.

        Guarantees provided by buildd's setup:

            - configured /etc/environment

            - configured hostname

            - networking available (IP & DNS resolution)

            - apt cache up-to-date

            - snapd configured and ready

            - system services are started and ready

        Additional guarantees provided by Charmcraft's setup:

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
            executor.execute_run(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "python3-pip",
                    "python3-setuptools",
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as error:
            raise bases.BaseConfigurationError(
                brief="Failed to install python3-pip and python3-setuptools.",
            ) from error

        try:
            snap_installer.inject_from_host(
                executor=executor, snap_name="charmcraft", classic=True
            )
        except snap_installer.SnapInstallationError as error:
            raise bases.BaseConfigurationError(
                brief="Failed to inject host Charmcraft snap into target environment.",
            ) from error
