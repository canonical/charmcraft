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
"""Utility functions for craft-parts plugins."""

import pathlib
import shlex
import textwrap
from collections.abc import Collection


def extend_python_build_environment(environment: dict[str, str]) -> dict[str, str]:
    """Extend the build environment for all Python plugins.

    :param environment: the existing environment dictionary
    :returns: the environment dictionary with charmcraft-specific additions.
    """
    return environment | {
        "PARTS_PYTHON_VENV_ARGS": "--without-pip",
    }


def get_charm_copy_commands(
    build_dir: pathlib.Path, install_dir: pathlib.Path
) -> Collection[str]:
    """Get the commands to copy charm source and charmlibs into the install directory.

    The commands will only be included if the relevant directories exist.
    """
    copy_command_base = ["cp", "--archive", "--recursive", "--reflink=auto"]
    src_dir = build_dir / "src"
    libs_dir = build_dir / "lib"

    commands = []
    if src_dir.exists():
        commands.append(
            shlex.join([*copy_command_base, str(src_dir), str(install_dir)])
        )
    if libs_dir.exists():
        commands.append(
            shlex.join([*copy_command_base, str(libs_dir), str(install_dir)])
        )

    return commands


def get_venv_cleanup_commands(venv_path: pathlib.Path, *, keep_bins: bool) -> list[str]:
    """Get a script do Charmcraft-specific venv cleanup.

    :param venv_path: The path to the venv.
    :param keep_bins: Whether to keep the bin directory of the venv.
    :returns: A shell script to do this, as a string.
    """
    venv_bin = venv_path / "bin"
    venv_lib64 = venv_path / "lib64"
    if keep_bins:
        delete_bins = []
    else:
        delete_bins = [
            # Remove all files in venv_bin except `activate`
            "shopt -s extglob",
            f"rm -rf {venv_bin}/!(activate)",
            "shopt -u extglob",
        ]
    update_activate = [
        # Replace hard-coded path in `activate` with portable path
        # "\&" is escape for sed
        'sed -i \'s#^VIRTUAL_ENV=.*$#VIRTUAL_ENV="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." \\&> /dev/null \\&\\& pwd )"#\' '
        + str(venv_bin / "activate"),
    ]
    delete_lib64 = textwrap.dedent(f"""
        if [ -L '{venv_lib64}' ]; then
          rm -f '{venv_lib64}'
        fi
    """)

    return [*delete_bins, *update_activate, delete_lib64]
