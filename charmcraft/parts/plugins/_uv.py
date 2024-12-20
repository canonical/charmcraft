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
"""Charmcraft-specific uv plugin."""

from pathlib import Path

from craft_parts.plugins import uv_plugin
from overrides import override

from charmcraft import utils


class UvPlugin(uv_plugin.UvPlugin):
    @override
    def get_build_environment(self) -> dict[str, str]:
        return utils.extend_python_build_environment(super().get_build_environment())

    @override
    def _get_venv_directory(self) -> Path:
        return self._part_info.part_install_dir / "venv"

    @override
    def _get_pip(self) -> str:
        return 'uv pip --python="${PARTS_PYTHON_VENV_INTERP_PATH}"'

    @override
    def _get_package_install_commands(self) -> list[str]:
        # Find the `uv sync` command and modify it to not install the project
        orig_cmds = super()._get_package_install_commands()
        for idx, cmd in enumerate(orig_cmds):
            if cmd.startswith("uv sync"):
                orig_cmds[idx] += " --no-install-project"
                break

        return [
            *orig_cmds,
            *utils.get_charm_copy_commands(
                self._part_info.part_build_dir, self._part_info.part_install_dir
            ),
        ]

    @override
    def _should_remove_symlinks(self) -> bool:
        return True

    @override
    def get_build_commands(self) -> list[str]:
        return [
            *super().get_build_commands(),
            *utils.get_venv_cleanup_commands(
                self._get_venv_directory(), keep_bins=False
            ),
        ]
