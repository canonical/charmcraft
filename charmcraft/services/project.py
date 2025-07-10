# Copyright 2025 Canonical Ltd.
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
"""Project service for Charmcraft."""

import itertools

import craft_platforms
from craft_application.services.project import ProjectService as BaseProjectService
from typing_extensions import override

from charmcraft.models.charmcraft import BasesConfiguration


class ProjectService(BaseProjectService):
    @override
    def _app_render_legacy_platforms(self) -> dict[str, craft_platforms.PlatformDict]:
        """Convert a bases charm to a platforms charm."""
        raw = self.get_raw()
        if "bases" not in raw:
            return super()._app_render_legacy_platforms()

        bases_config = [
            BasesConfiguration.model_validate(base) for base in raw["bases"]
        ]

        platforms = {}

        for base in bases_config:
            platform_parts = [
                f"{run.name}-{run.channel}-{'-'.join(run.architectures)}"
                for run in base.run_on
            ]
            platform = "_".join(platform_parts)
            build_ons = list(
                itertools.chain.from_iterable(
                    build_on.to_strings() for build_on in base.build_on
                )
            )
            build_fors = list(
                itertools.chain.from_iterable(
                    build_for.to_strings() for build_for in base.run_on
                )
            )

            platforms[platform] = {
                "build-on": build_ons,
                "build-for": build_fors,
            }

        return platforms
