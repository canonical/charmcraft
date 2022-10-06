# Copyright 2022 Canonical Ltd.
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

"""Charmcraft-specific code to interface with craft-providers."""

import os
import pathlib
import sys
from typing import NamedTuple, List, Optional, Dict, TYPE_CHECKING

from craft_cli import emit, CraftError
from craft_providers import bases, Executor, ProviderError

from charmcraft.bases import check_if_base_matches_host
from charmcraft.config import Base, BasesConfiguration
from charmcraft.env import get_managed_environment_snap_channel, get_managed_environment_log_path
from charmcraft.utils import confirm_with_user

if TYPE_CHECKING:
    from charmcraft.providers import Provider


BASE_CHANNEL_TO_PROVIDER_BASE = {
    "18.04": bases.BuilddBaseAlias.BIONIC,
    "20.04": bases.BuilddBaseAlias.FOCAL,
    "22.04": bases.BuilddBaseAlias.JAMMY,
}


class Plan(NamedTuple):
    """A build plan for a particular base.

    :param bases_config: The BasesConfiguration object, which contains a list of Bases to
      build on and a list of Bases to run on.
    :param build_on: The Base to build on.
    :param bases_index: Index of the BasesConfiguration in bases_config containing the
      Base to build on.
    :param build_on_index: Index of the Base to build on in the BasesConfiguration's build_on list.
    """

    bases_config: BasesConfiguration
    build_on: Base
    bases_index: int
    build_on_index: int


def create_build_plan(
    *,
    bases: Optional[List[BasesConfiguration]],
    bases_indices: Optional[List[int]],
    destructive_mode: bool,
    managed_mode: bool,
    provider: "Provider",
) -> List[Plan]:
    """Determine the build plan based on user inputs and host environment.

    Provide a list of bases that are buildable and scoped according to user
    configuration. Provide all relevant details including the applicable
    bases configuration and the indices of the entries to build for.

    :param bases: List of BaseConfigurations
    :param bases_indices: List of indices of which BaseConfigurations to consider when creating
      the build plan. If None, then all BaseConfigurations are considered
    :param destructive_mode: True is charmcraft is running in destructive mode
    :param managed_mode: True is charmcraft is running in managed mode
    :param provider: Provider object to check for base availability

    :returns: List of Plans
    :raises CraftError: if no bases are provided.
    """
    build_plan: List[Plan] = []

    if not bases:
        raise CraftError("Cannot create build plan because no bases were provided.")

    for bases_index, bases_config in enumerate(bases):
        if bases_indices and bases_index not in bases_indices:
            emit.debug(f"Skipping 'bases[{bases_index:d}]' due to --base-index usage.")
            continue

        for build_on_index, build_on in enumerate(bases_config.build_on):
            if managed_mode or destructive_mode:
                matches, reason = check_if_base_matches_host(build_on)
            else:
                matches, reason = provider.is_base_available(build_on)

            if matches:
                emit.debug(
                    f"Building for 'bases[{bases_index:d}]' "
                    f"as host matches 'build-on[{build_on_index:d}]'.",
                )
                build_plan.append(Plan(bases_config, build_on, bases_index, build_on_index))
                break
            else:
                emit.progress(
                    f"Skipping 'bases[{bases_index:d}].build-on[{build_on_index:d}]': "
                    f"{reason}.",
                )
        else:
            emit.progress(
                "No suitable 'build-on' environment found "
                f"in 'bases[{bases_index:d}]' configuration.",
                permanent=True,
            )

    return build_plan


def get_command_environment() -> Dict[str, str]:
    """Construct the required environment."""
    env = bases.buildd.default_command_environment()
    env["CHARMCRAFT_MANAGED_MODE"] = "1"

    # Pass-through host environment that target may need.
    for env_key in ["http_proxy", "https_proxy", "no_proxy"]:
        if env_key in os.environ:
            env[env_key] = os.environ[env_key]

    return env


def get_instance_name(
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


def get_base_configuration(
    *,
    alias: bases.BuilddBaseAlias,
    instance_name: str,
) -> bases.BuilddBase:
    """Create a BuilddBase configuration."""
    environment = get_command_environment()

    # injecting a snap on a non-linux system is not supported, so default to
    # install charmcraft from the store's stable channel
    snap_channel = get_managed_environment_snap_channel()
    if snap_channel is None and sys.platform != "linux":
        snap_channel = "stable"

    charmcraft_snap = bases.buildd.Snap(name="charmcraft", channel=snap_channel, classic=True)
    return bases.BuilddBase(
        alias=alias,
        environment=environment,
        hostname=instance_name,
        snaps=[charmcraft_snap],
        compatibility_tag=f"charmcraft-{bases.BuilddBase.compatibility_tag}.0",
    )


def capture_logs_from_instance(instance: Executor) -> None:
    """Retrieve logs from instance.

    :param instance: Instance to retrieve logs from.
    """
    source_log_path = get_managed_environment_log_path()
    with instance.temporarily_pull_file(source=source_log_path, missing_ok=True) as local_log_path:
        if local_log_path:
            emit.debug("Logs captured from managed instance:")
            with open(local_log_path, "rt", encoding="utf8") as fh:
                for line in fh:
                    emit.debug(f":: {line.rstrip()}")
        else:
            emit.debug("No logs found in instance.")
            return


def ensure_provider_is_available(provider: "Provider") -> None:
    """Ensure provider is installed, running, and properly configured.

    If the provider is not installed, the user is prompted to install it.

    :param instance: the provider to ensure is available
    :raises ProviderError: if provider is not available, or if the user
    chooses not to install the provider.
    """
    confirm_msg = (
        f"{provider.name} is required but not installed. Do you wish to "
        f"install {provider.name} and configure it with the defaults?"
    )
    if not provider.is_provider_installed() and not confirm_with_user(confirm_msg, default=False):
        raise ProviderError(
            f"{provider.name} is required, but not installed. {provider.install_recommendation}"
        )
    provider.ensure_provider_is_available()
