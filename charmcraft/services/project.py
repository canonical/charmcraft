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
import pathlib

import craft_platforms
from craft_application.services.project import ProjectService as BaseProjectService
from craft_cli import CraftError
from typing_extensions import Any, override

from charmcraft import const, extensions, preprocess
from charmcraft.models.charmcraft import BasesConfiguration


class ProjectService(BaseProjectService):
    """Charmcraft-specific project service."""

    @override
    def _app_render_legacy_platforms(self) -> dict[str, craft_platforms.PlatformDict]:
        """Convert a bases charm to a platforms charm."""
        raw = self.get_raw()
        if "bases" not in raw:
            return super()._app_render_legacy_platforms()

        bases_config = [
            BasesConfiguration.model_validate(base) for base in raw["bases"]
        ]

        platforms: dict[str, craft_platforms.PlatformDict] = {}
        invalid_build_bases: set[str] = set()

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
            for build_on in base.build_on:
                if (build_str := build_on.to_os_string()) not in const.LEGACY_BASES:
                    invalid_build_bases.add(build_str)

            platforms[platform] = {
                "build-on": build_ons,
                "build-for": build_fors,
            }

        if invalid_build_bases:
            bases_str = ", ".join(f"'{base}'" for base in sorted(invalid_build_bases))
            brief = f"Not valid for use with the 'bases' key: {bases_str}"
            raise CraftError(
                brief,
                resolution="Use the 'platforms' keyword in order to use newer bases.",
            )

        return platforms

    @override
    @staticmethod
    def _app_preprocess_project(
        project: dict[str, Any],
        *,
        build_on: str,
        build_for: str,
        platform: str,
    ) -> None:
        """Run Charmcraft-specific pre-processing on the project."""
        # Extensions get applied on as close as possible to what the user provided.
        project_dir = pathlib.Path.cwd()
        extensions.apply_extensions(project_dir, project)
        # Preprocessing "magic" to create a fully-formed charm.
        preprocess.add_default_parts(project)
        preprocess.add_config(project_dir, project)
        preprocess.add_actions(project_dir, project)
        preprocess.add_metadata(project_dir, project)
