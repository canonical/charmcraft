# Copyright 2023 Canonical Ltd.
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
"""Bundle plugin for craft-parts."""
import sys
from typing import Any, Dict, List, Set

from craft_parts import plugins


class BundlePluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """Properties used to pack bundles."""

    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate bundle properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = plugins.extract_plugin_properties(
            data, plugin_name="bundle", required=["source"]
        )
        return cls(**plugin_data)


class BundlePlugin(plugins.Plugin):
    """Prepare a bundle for packing.

    Extra files to be included in the bundle payload must be listed under
    the ``prime`` file filter.
    """

    properties_class = BundlePluginProperties

    @classmethod
    def get_build_snaps(cls) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        install_dir = self._part_info.part_install_dir
        if sys.platform == "linux":
            cp_cmd = "cp --archive --link --no-dereference"
        else:
            cp_cmd = "cp -R -p -P"

        return [
            f'mkdir -p "{install_dir}"',
            f'{cp_cmd} * "{install_dir}"',
        ]
