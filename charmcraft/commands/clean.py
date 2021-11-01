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

"""Infrastructure for the 'clean' command."""

from craft_cli import emit

from charmcraft.cmdbase import BaseCommand
from charmcraft.metadata import parse_metadata_yaml
from charmcraft.providers import get_provider

_overview = """
Purge Charmcraft project's artifacts, including:

- LXD Containers created for building charm(s)
"""


class CleanCommand(BaseCommand):
    """Clean project artifacts."""

    name = "clean"
    help_msg = "Purge project artifacts"
    overview = _overview
    common = True

    def run(self, parsed_args):
        """Run the command."""
        project_path = self.config.project.dirpath
        metadata = parse_metadata_yaml(project_path)
        emit.progress(f"Cleaning project {metadata.name!r}.")

        provider = get_provider()
        provider.clean_project_environments(charm_name=metadata.name, project_path=project_path)
        emit.message(f"Cleaned project {metadata.name!r}.")
