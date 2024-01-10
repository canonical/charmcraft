# Copyright 2024 Canonical Ltd.
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
"""Library related commands."""
import argparse
import pathlib
import textwrap

from craft_cli import emit

from charmcraft import errors, utils
from charmcraft.application.commands.base import CharmcraftCommand


class FetchLibsCommand(CharmcraftCommand):
    """Fetch charm libraries.

    Spec: https://docs.google.com/document/d/1Y2TlTrWCkrHKCKDxaxISXQwvN_tkoDEvPU1fY9yI3WQ/view
    """

    name = "fetch-libs"
    help_msg = "Fetch or update charm libraries defined in charmcraft.yaml"
    overview = textwrap.dedent(
        """
        Fetch charm libraries defined in charmcraft.yaml.

        Fetches the libraries specified under the 'charm-libs' key in charmcraft.yaml.
        """
    )
    always_load_project = True

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the command."""
        charm_libs = self._services.project.charm_libs
        if not charm_libs:
            raise errors.NoCharmLibsError(self.name)
        emit.debug(f"Libraries to fetch: {charm_libs}")

        project_path = pathlib.Path(self._global_args.get("project_dir") or ".")
        charms_path = project_path / "lib" / "charms"

        with emit.progress_bar(f"Fetching {len(charm_libs)} libraries", len(charm_libs)) as bar:
            for lib in self._services.store.fetch_libraries(charm_libs):
                lib_path = utils.get_lib_path(
                    charms_path, lib.charm_name, lib.lib_name, lib.api
                )
                lib_path.parent.mkdir(parents=True, exist_ok=True)
                lib_path.write_text(str(lib.content))
                bar.advance(1)
