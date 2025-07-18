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
"""Charmcraft-specific build planning service."""

from collections.abc import Iterable
from typing import Any

import craft_platforms
from craft_application.services.buildplan import BuildPlanService


class CharmBuildPlanService(BuildPlanService):
    """A service for generating and filtering build plans."""

    def _gen_exhaustive_build_plan(
        self, project_data: dict[str, Any]
    ) -> Iterable[craft_platforms.BuildInfo]:
        """Generate the exhaustive build plan with craft-platforms.

        :param project_data: The unprocessed project data retrieved from a YAML file.
        :returns: An iterable of BuildInfo objects that make the exhaustive build plan.
        """
        raw_project = self._services.get("project").get_raw()
        if "platforms" in raw_project:
            project_data["platforms"] = raw_project["platforms"]
        else:
            del project_data["platforms"]
        return super()._gen_exhaustive_build_plan(project_data=project_data)
