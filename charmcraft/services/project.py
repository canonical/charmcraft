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
"""Project service for charmcraft."""

import itertools

import craft_platforms
from craft_application.errors import CraftValidationError
from craft_application.services import project

from charmcraft.models.charmcraft import BasesConfiguration


class ProjectService(project.ProjectService):
    """Project service for Charmcraft."""

    def _app_render_legacy_platforms(self) -> dict[str, craft_platforms.PlatformDict]:
        """Render platforms from a 'bases' key."""
        raw_file = self.get_raw()

        raw_bases = raw_file.get("bases")
        if not raw_bases:
            if raw_file.get("type") == "bundle":
                # Bundles are machine independent, so we just create a single bundle
                # platform that builds anywhere.
                return {
                    "bundle": {
                        "build-on": ["amd64", "arm64", "ppc64el", "riscv64", "s390x"],
                        "build-for": ["all"],
                    }
                }
            raise CraftValidationError(
                "Cannot find a 'platforms' or 'bases' key in charmcraft.yaml.",
                resolution="Add a 'platforms' key to charmcraft.yaml.",
                docs_url="https://canonical-charmcraft.readthedocs-hosted.com/en/stable/howto/build-guides/select-platforms/",
                logpath_report=False,
                reportable=False,
                retcode=65,  #  os.EX_DATAERR
            )

        bases = [BasesConfiguration.unmarshal(base) for base in raw_bases]
        platforms = {}
        for bases_index, base_config in enumerate(bases):
            platform_name = "_".join(str(base) for base in base_config.run_on)
            build_on = itertools.chain.from_iterable(
                base.to_platforms() for base in base_config.build_on
            )
            build_for = itertools.chain.from_iterable(
                base.to_platforms() for base in base_config.run_on
            )
            platforms[platform_name] = {
                "build-on": list(build_on),
                "build-for": list(build_for),
                "bases-index": bases_index,
            }

        return platforms
