# Copyright 2024 Canonical Ltd.
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

"""Charmcraft-specific poetry plugin."""

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Literal, cast

from craft_parts.plugins.base import BasePythonPlugin
import overrides
from craft_parts.plugins import poetry_plugin
from craft_parts.errors import PluginEnvironmentValidationError


class PoetryPlugin(poetry_plugin.PoetryPlugin):
    """Charmcraft-specific version of the poetry plugin."""

    def get_build_environment(self) -> dict[str, str]:
        return super().get_build_environment() | {
            "PATH": "$HOME/.local/bin:$PATH",
        }

    def get_build_packages(self) -> set[str]:
        return super(poetry_plugin.PoetryPlugin, self).get_build_packages() | {"curl"}

    def get_pull_commands(self) -> list[str]:
        if not self._system_has_poetry():
            install_poetry = ["curl -sSL https://install.python-poetry.org | python3 -"]
        else:
            install_poetry = []
        return [*super().get_pull_commands(), *install_poetry]

    def _get_venv_directory(self) -> Path:
        return self._part_info.part_install_dir / "venv"

    def _get_pip_command(self) -> str:
        """Get the pip command for installing the package and its dependencies."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"
        return f"{self._get_pip()} install --requirement={requirements_path}"

    def _get_package_install_commands(self) -> list[str]:
        return [
            *super()._get_package_install_commands(),
            f"cp -arf {self._part_info.part_build_dir}/src {self._part_info.part_install_dir}",
            f"cp -arf {self._part_info.part_build_dir}/lib {self._part_info.part_install_dir}"
        ]

    def _should_remove_symlinks(self) -> bool:
        """Configure executables symlink removal.

        This method can be overridden by application-specific subclasses to control
        whether symlinks in the virtual environment should be removed. Default is
        False.  If True, the venv-created symlinks to python* in bin/ will be
        removed and will not be recreated.
        """
        return True
