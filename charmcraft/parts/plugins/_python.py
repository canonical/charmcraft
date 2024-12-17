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

import shlex
from pathlib import Path

from craft_parts.plugins import python_plugin
from overrides import override

from charmcraft import utils


class PythonPluginProperties(python_plugin.PythonPluginProperties, frozen=True):
    python_packages: list[str] = []  # No default packages.
    python_keep_bins: bool = False
    """Keep the virtual environment's 'bin' directory."""


class PythonPlugin(python_plugin.PythonPlugin):
    """Charmcraft-specific version of the python plugin."""

    properties_class = PythonPluginProperties
    _options: PythonPluginProperties  # type: ignore[reportIncompatibleVariableOverride]

    @override
    def get_build_environment(self) -> dict[str, str]:
        return {
            "PIP_NO_BINARY": ":all:",
        } | utils.extend_python_build_environment(super().get_build_environment())

    @override
    def _get_venv_directory(self) -> Path:
        return self._part_info.part_install_dir / "venv"

    @override
    def _get_pip(self) -> str:
        """Get the pip command to use."""
        return f"{self._get_system_python_interpreter()} -m pip --python=${{PARTS_PYTHON_VENV_INTERP_PATH}}"

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Get the package installation commands.

        This overrides the generic class in the following ways:

        1. Doesn't try to install '.' (charms are not installable packages)
        2. Copy the charm source into the charm.
        3. Copy the charmlibs into the charm.
        """
        pip = self._get_pip()
        install_params = shlex.join(
            (
                *(
                    f"--constraint={constraint}"
                    for constraint in self._options.python_constraints
                ),
                *(
                    f"--requirement={requirement}"
                    for requirement in self._options.python_requirements
                ),
                *self._options.python_packages,
            )
        )
        return [
            f"{pip} install --no-deps {install_params}",
            f"{pip} check",
            *utils.get_charm_copy_commands(
                self._part_info.part_build_dir, self._part_info.part_install_dir
            ),
        ]

    @override
    def _should_remove_symlinks(self) -> bool:
        return True

    @override
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
                self._get_venv_directory(), keep_bins=self._options.python_keep_bins
            ),
        ]
