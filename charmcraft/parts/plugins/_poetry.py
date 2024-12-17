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
"""Charmcraft-specific poetry plugin."""

import pathlib
import shlex
from pathlib import Path

from craft_parts.plugins import poetry_plugin
from overrides import override

from charmcraft import utils


class PoetryPluginProperties(poetry_plugin.PoetryPluginProperties, frozen=True):
    poetry_keep_bins: bool = False
    """Keep the virtual environment's 'bin' directory."""


class PoetryPlugin(poetry_plugin.PoetryPlugin):
    """Charmcraft-specific version of the poetry plugin."""

    properties_class = PoetryPluginProperties
    _options: PoetryPluginProperties  # type: ignore[reportIncompatibleVariableOverride]

    def get_build_environment(self) -> dict[str, str]:
        return utils.extend_python_build_environment(super().get_build_environment())

    def _get_venv_directory(self) -> Path:
        return self._part_info.part_install_dir / "venv"

    def _get_pip(self) -> str:
        """Get the pip command to use."""
        return f"{self._get_system_python_interpreter()} -m pip --python=${{PARTS_PYTHON_VENV_INTERP_PATH}}"

    def _get_pip_install_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for installing with pip.

        This only installs the dependencies from requirements, unlike the upstream
        version, because charms are not installable Python packages.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the install script.
        """
        pip = self._get_pip()
        pip_extra_args = shlex.join(self._options.poetry_pip_extra_args)
        return [
            # These steps need to be separate because poetry export defaults to including
            # hashes, which don't work with installing from a directory.
            f"{pip} install --no-deps --no-binary=:all: {pip_extra_args} '--requirement={requirements_path}'",
            # Check that the virtualenv is consistent.
            f"{pip} check",
        ]

    def _get_package_install_commands(self) -> list[str]:
        """Get the package installation commands.

        This overrides the generic class to also:

        1. Copy the charm source into the charm.
        2. Copy the charmlibs into the charm.
        """
        return [
            *super()._get_package_install_commands(),
            *utils.get_charm_copy_commands(
                self._part_info.part_build_dir, self._part_info.part_install_dir
            ),
        ]

    def _should_remove_symlinks(self) -> bool:
        return True

    def _get_rewrite_shebangs_commands(self) -> list[str]:
        """Get the commands used to rewrite shebangs in the install dir.

        Charms don't need the shebangs to be rewritten.
        """
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Get the build commands for the Python plugin."""
        return [
            *super().get_build_commands(),
            *utils.get_venv_cleanup_commands(
                self._get_venv_directory(), keep_bins=self._options.poetry_keep_bins
            ),
        ]
