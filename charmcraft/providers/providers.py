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

from typing import NamedTuple, List, Optional

from craft_cli import emit, CraftError

from charmcraft.bases import check_if_base_matches_host
from charmcraft.config import Base, BasesConfiguration
from charmcraft.providers import Provider


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
    provider: Provider,
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
