# Copyright 2021-2022 Canonical Ltd.
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

"""Infrastructure for the 'clean' command."""

from craft_cli import emit

from charmcraft.cmdbase import BaseCommand
from charmcraft.metadata import parse_metadata_yaml
from charmcraft.providers import get_provider
from charmcraft.providers.providers import create_build_plan, get_instance_name
from charmcraft.utils import get_host_architecture

_overview = """
Purge Charmcraft project's artifacts, including:

- LXD Containers created for building charm(s)
- Multipass Containers created for building charm(s)
"""


class CleanCommand(BaseCommand):
    """Clean project artifacts."""

    name = "clean"
    help_msg = "Purge project artifacts"
    overview = _overview
    common = True

    def run(self, parsed_args):
        """Run the clean command.

        First, a build plan is created.
        Then each item in the build plan is cleaned.
        """
        project_path = self.config.project.dirpath
        metadata = parse_metadata_yaml(project_path)
        emit.message(f"Cleaning project {metadata.name!r}.")
        provider = get_provider()
        build_plan = create_build_plan(
            bases=self.config.bases,
            bases_indices=None,
            destructive_mode=False,
            managed_mode=False,
            provider=provider,
        )

        for plan in build_plan:
            instance_name = get_instance_name(
                project_name=metadata.name,
                project_path=project_path,
                bases_index=plan.bases_index,
                build_on_index=plan.build_on_index,
                target_arch=get_host_architecture(),
            )

            emit.debug(f"Cleaning environment {instance_name!r}")
            provider.clean_project_environments(instance_name=instance_name)

        emit.message(f"Cleaned project {metadata.name!r}.")
