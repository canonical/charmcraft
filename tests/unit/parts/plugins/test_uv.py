import sys
from pathlib import Path

import pytest
import pytest_check

from charmcraft.parts import plugins

pytestmark = [
    pytest.mark.skipif(sys.platform == "win32", reason="Windows not supported")
]


def test_get_build_environment(uv_plugin: plugins.UvPlugin):
    env = uv_plugin.get_build_environment()

    assert env["PIP_NO_BINARY"] == ":all:"


def test_get_venv_directory(uv_plugin: plugins.UvPlugin, install_path: Path):
    assert uv_plugin._get_venv_directory() == install_path / "venv"


def test_get_package_install_commands(
    uv_plugin: plugins.UvPlugin, build_path: Path, install_path: Path
):
    copy_src_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/src {install_path}"
    )

    copy_lib_cmd = (
        f"cp --archive --recursive --reflink=auto {build_path}/lib {install_path}"
    )

    default_commands = uv_plugin._get_package_install_commands()

    pytest_check.is_not_in(copy_src_cmd, default_commands)
    pytest_check.is_not_in(copy_lib_cmd, default_commands)

    (build_path / "src").mkdir(parents=True)

    pytest_check.equal(
        uv_plugin._get_package_install_commands(), [*default_commands, copy_src_cmd]
    )

    (build_path / "lib" / "charm").mkdir(parents=True)

    pytest_check.equal(
        uv_plugin._get_package_install_commands(),
        [*default_commands, copy_src_cmd, copy_lib_cmd],
    )

    (build_path / "src").rmdir()

    pytest_check.equal(
        uv_plugin._get_package_install_commands(), [*default_commands, copy_lib_cmd]
    )
