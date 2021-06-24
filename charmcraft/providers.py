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
import os
import subprocess
from typing import Dict, Optional

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

logger = logging.getLogger(__name__)


def get_command_environment() -> Dict[str, str]:
    """Construct the required environment."""
    env = bases.buildd.default_command_environment()
    env["CHARMCRAFT_MANAGED_MODE"] = "1"

    # Pass-through host environment that target may need.
    for env_key in ["http_proxy", "https_proxy", "no_proxy"]:
        if env_key in os.environ:
            env[env_key] = os.environ[env_key]

    return env


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
