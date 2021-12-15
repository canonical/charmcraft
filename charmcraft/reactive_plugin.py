# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Charmcraft's reactive plugin for craft-parts."""

import subprocess
from typing import Any, Dict, List, Optional, Set

from craft_cli import emit
from craft_parts import plugins
from craft_parts.errors import PluginEnvironmentValidationError


class ReactivePluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """Properties used to pack reactive charms using charm-tools."""

    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate reactive plugin properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = plugins.extract_plugin_properties(
            data, plugin_name="reactive", required=["source"]
        )
        return cls(**plugin_data)


class ReactivePluginEnvironmentValidator(plugins.validator.PluginEnvironmentValidator):
    """Check the execution environment for the Reactive plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If the environment is invalid.
        """
        try:
            output = self._execute("charm version").strip()
            client_version, tools_version = output.split("\n")

            if not tools_version.startswith("charm-tools"):
                raise PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"invalid charm tools version {tools_version}",
                )
            emit.trace(f"found {tools_version}")
        except ValueError as err:
            raise PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason="invalid charm tools installed",
            ) from err
        except subprocess.CalledProcessError as err:
            if err.returncode != plugins.validator.COMMAND_NOT_FOUND:
                raise PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"charm tools failed with error code {err.returncode}",
                ) from err

            if part_dependencies is None or "charm-tools" not in part_dependencies:
                raise PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=(
                        f"charm tool not found and part {self._part_name!r} "
                        f"does not depend on a part named 'charm-tools'"
                    ),
                ) from err


class ReactivePlugin(plugins.Plugin):
    """Build a reactive charm using charm-tools."""

    properties_class = ReactivePluginProperties
    validator_class = ReactivePluginEnvironmentValidator

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
        name = self._part_info.project_name
        commands = [
            "rm -f charmcraft.yaml",
            # exit on errors (code 200), warnings (code 100) allowed
            'charm proof || test "$?" -ge 200 && exit 1',
            f'mkdir -p "{install_dir}"',
            f'ln -sf . "{install_dir}/{name}"',
            f'charm build -o "{install_dir}" || test "$?" -ge 200 && exit 1',
            f'rm -f "{install_dir}/{name}"',
        ]
        return commands
