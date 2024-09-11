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

POETRY_INSTALL_COMMAND = "curl -sSL https://install.python-poetry.org | python3 -"


class PoetryPlugin(poetry_plugin.PoetryPlugin):
    """Charmcraft-specific version of the poetry plugin."""

    def get_build_environment(self) -> dict[str, str]:
        env = super().get_build_environment() | {
            "PIP_NO_BINARY": ":all:",  # Build from source
        }

        # Needed for installing poetry through its install script.
        old_path = env.get("PATH", "${PATH}")
        env["PATH"] = f"${{HOME}}/.local/bin:{old_path}"

        return env

    def get_build_packages(self) -> set[str]:
        return super(poetry_plugin.PoetryPlugin, self).get_build_packages() | {"curl"}

    def get_pull_commands(self) -> list[str]:
        install_poetry = [] if self._system_has_poetry() else [POETRY_INSTALL_COMMAND]
        return [*super().get_pull_commands(), *install_poetry]

    def _get_venv_directory(self) -> Path:
        return self._part_info.part_install_dir / "venv"

    def _get_pip_install_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for installing with pip.

        This only installs the dependencies from requirements, unlike the upstream version.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the install script.
        """
        pip = self._get_pip()
        return [
            # These steps need to be separate because poetry export defaults to including
            # hashes, which don't work with installing from a directory.
            f"{pip} install --no-deps --requirement={requirements_path}",
            # Check that the virtualenv is consistent.
            f"{pip} check",
        ]

    def _get_package_install_commands(self) -> list[str]:
        """Get the package installation commands.

        This overrides the generic class to also:

        1. Copy the charm source into the charm.
        2. Copy the charmlibs into the charm.
        """
        commands = super()._get_package_install_commands()
        copy_command_base = ["cp", "--archive", "--recursive", "--reflink=auto"]
        src_dir = self._part_info.part_build_dir / "src"
        libs_dir = self._part_info.part_build_dir / "lib"
        install_dir = str(self._part_info.part_install_dir)
        # Copy charm source and libs if they exist.
        if src_dir.exists():
            commands.append(shlex.join([*copy_command_base, str(src_dir), install_dir]))
        if libs_dir.exists():
            commands.append(shlex.join([*copy_command_base, str(libs_dir), install_dir]))
        return commands

    def _should_remove_symlinks(self) -> bool:
        return True
