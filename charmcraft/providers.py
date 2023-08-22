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

import enum
import os
import pathlib
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from craft_cli import CraftError, emit
from craft_providers import Base, Executor, Provider, ProviderError, lxd, multipass
from craft_providers.actions.snap_installer import Snap
from craft_providers.bases import (
    BASE_NAME_TO_BASE_ALIAS,
    get_base_alias,
    get_base_from_alias,
)
from craft_providers.errors import BaseConfigurationError

from charmcraft.bases import check_if_base_matches_host
from charmcraft.env import (
    get_managed_environment_log_path,
    get_managed_environment_snap_channel,
    is_charmcraft_running_from_snap,
    is_charmcraft_running_in_developer_mode,
)
from charmcraft.models.charmcraft import BasesConfiguration
from charmcraft.snap import get_snap_configuration
from charmcraft.utils import confirm_with_user, get_host_architecture


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
                matches, reason = is_base_available(build_on)

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


def get_command_environment(base: Base) -> Dict[str, str]:
    """Construct the required environment."""
    env = base.default_command_environment()
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
    alias: enum.Enum,
    instance_name: str,
) -> Base:
    """Create a Base configuration."""
    # injecting a snap on a non-linux system is not supported, so default to
    # install charmcraft from the store's stable channel
    snap_channel = get_managed_environment_snap_channel()
    if snap_channel is None and sys.platform != "linux":
        snap_channel = "stable"

    base = get_base_from_alias(alias)
    charmcraft_snap = Snap(name="charmcraft", channel=snap_channel, classic=True)
    environment = get_command_environment(base)
    return base(
        alias=alias,
        environment=environment,
        hostname=instance_name,
        snaps=[charmcraft_snap],
        compatibility_tag=f"charmcraft-{base.compatibility_tag}.0",
    )


def capture_logs_from_instance(instance: Executor) -> None:
    """Retrieve logs from instance.

    :param instance: Instance to retrieve logs from.
    """
    source_log_path = get_managed_environment_log_path()
    with instance.temporarily_pull_file(source=source_log_path, missing_ok=True) as local_log_path:
        if local_log_path:
            emit.debug("Logs captured from managed instance:")
            with open(local_log_path, encoding="utf8") as fh:
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
    # TODO: add provider.name and provider.install_recommendations to craft-providers
    confirm_msg = (
        "Provider is required but not installed. Do you wish to "
        "install provider and configure it with the defaults?"
    )
    if not provider.is_provider_installed() and not confirm_with_user(confirm_msg, default=False):
        raise ProviderError("Provider is required, but not installed.")
    provider.ensure_provider_is_available()


def is_base_available(base: Base) -> Tuple[bool, Union[str, None]]:
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

    if base.name not in ("ubuntu", "centos", "almalinux"):
        return (
            False,
            f"name {base.name!r} is not yet supported (must be 'ubuntu', 'almalinux', "
            "or 'centos')",
        )

    try:
        get_base_alias((base.name, base.channel))
    except BaseConfigurationError:
        *firsts, last = sorted(" ".join(s) for s in BASE_NAME_TO_BASE_ALIAS)
        allowed = f"{', '.join(map(repr, firsts))} or {last!r}"
        return (
            False,
            f"base {base.name!r} channel {base.channel!r} is not yet supported "
            f"(must be {allowed})",
        )

    return True, None


def _get_platform_default_provider() -> str:
    if sys.platform == "linux":
        return "lxd"

    return "multipass"


def get_provider():
    """Get the configured or appropriate provider for the host OS.

    If platform is not Linux, use Multipass.

    If platform is Linux:
    (1) use provider specified with CHARMCRAFT_PROVIDER if running
        in developer mode,
    (2) use provider specified with snap configuration if running
        as snap,
    (3) default to platform default (LXD on Linux).

    :return: Provider instance.
    """
    provider = None

    if is_charmcraft_running_in_developer_mode():
        provider = os.getenv("CHARMCRAFT_PROVIDER")

    if provider is None and is_charmcraft_running_from_snap():
        snap_config = get_snap_configuration()
        provider = snap_config.provider if snap_config else None

    if provider is None:
        provider = _get_platform_default_provider()

    if provider == "lxd":
        return lxd.LXDProvider(lxd_project="charmcraft")
    elif provider == "multipass":
        return multipass.MultipassProvider()

    raise CraftError(f"Unsupported provider specified {provider!r}.")
