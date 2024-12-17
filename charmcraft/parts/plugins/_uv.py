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
        return [
            *super()._get_package_install_commands(),
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
