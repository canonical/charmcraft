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
from typing import Optional, Tuple, Union

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

from charmcraft.config import Base
from charmcraft.utils import get_host_architecture

logger = logging.getLogger(__name__)

BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS = {
    "18.04": bases.BuilddBaseAlias.BIONIC,
    "20.04": bases.BuilddBaseAlias.FOCAL,
}


def is_base_providable(base: Base) -> Tuple[bool, Union[str, None]]:
    """Check if provider can provide an environment matching given base.

    :param base: Base to check.

    :returns: Tuple of bool indicating whether it is a match, with optional
              reason if not a match.
    """
    host_arch = get_host_architecture()
    if host_arch not in base.architectures:
        return (
            False,
            f"host architecture {host_arch!r} not in base architectures {base.architectures!r}",
        )

    if base.name != "ubuntu":
        return (
            False,
            f"name {base.name!r} is not yet supported (must be 'ubuntu')",
        )

    if base.channel not in BASE_CHANNEL_TO_BUILDD_IMAGE_ALIAS.keys():
        return (
            False,
            f"channel {base.channel!r} is not yet supported (must be '18.04' or '20.04')",
        )

    return True, None


def get_instance_name(
    *, bases_index: int, build_on_index: int, project_name: str, target_arch: str
) -> str:
    """Formulate the name for an instance using each of the given parameters.

    Incorporate each of the parameters into the name to come up with a
    predictable naming schema that avoids name collisions across multiple,
    potentially complex, projects.

    :param bases_index: Index of `bases:` entry.
    :param build_on_index: Index of `build-on` within bases entry.
    :param project_name: Name of charm project.
    :param target_arch: Targetted architecture, used in the name to prevent
        collisions should future work enable multiple architectures on the same
        platform.
    """
    return "-".join(
        [
            "charmcraft",
            project_name,
            str(bases_index),
            str(build_on_index),
            target_arch,
        ]
    )


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
