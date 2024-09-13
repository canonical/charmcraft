# Copyright 2021-2024 Canonical Ltd.
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

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Literal, cast

import overrides
from craft_parts import plugins
from craft_parts.errors import PluginEnvironmentValidationError


class ReactivePluginProperties(plugins.PluginProperties, frozen=True):
    """Properties used to pack reactive charms using charm-tools."""

    plugin: Literal["reactive"] = "reactive"
    source: str = "."
    reactive_charm_build_arguments: list[str] = []


class ReactivePluginEnvironmentValidator(plugins.validator.PluginEnvironmentValidator):
    """Check the execution environment for the Reactive plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: list[str] | None = None):
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If the environment is invalid.
        """
        try:
            version_data = json.loads(self._execute("charm version --format json"))

            tool_name = "charm-tools"
            if not (
                tool_name in version_data
                and "version" in version_data[tool_name]
                and "git" in version_data[tool_name]
            ):
                raise PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"invalid charm tools version {version_data}",
                )
            tools_version = (
                f"{tool_name} {version_data[tool_name]['version']} "
                f"({version_data[tool_name]['git']})"
            )
            print(f"found {tools_version}")
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

    @overrides.override
    def get_build_snaps(cls) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            # Cryptography fails to load OpenSSL legacy provider in some circumstances.
            # Since we don't need the legacy provider, this works around that bug.
            "CRYPTOGRAPHY_OPENSSL_NO_LEGACY": "true"
        }

    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(ReactivePluginProperties, self._options)

        command = [
            sys.executable,
            "-I",
            __file__,
            self._part_info.project_name,
            str(self._part_info.part_build_dir),
            str(self._part_info.part_install_dir),
        ]
        # The YAML List[str] schema would colocate any options with arguments
        # in the same string.  This is not what we want as we need to send
        # these separately when calling out to the command later.
        #
        # Expand any such strings as we add them to the command.
        for arg in options.reactive_charm_build_arguments:
            command.extend(shlex.split(arg))
        return [" ".join(shlex.quote(i) for i in command)]


def run_charm_tool(args: list[str]):
    """Run the charm tool, log and check exit code."""
    result_classification = "SUCCESS"
    exc = None

    print(f"charm tool execution command={args}")
    try:
        completed_process = subprocess.run(args, check=True)
    except subprocess.CalledProcessError as call_error:
        exc = call_error
        if call_error.returncode < 100 or call_error.returncode >= 200:
            result_classification = "ERROR"
            raise
        result_classification = "WARNING"
        print(f"charm tool execution {result_classification}: returncode={exc.returncode}")
    else:
        print(
            f"charm tool execution {result_classification}: returncode={completed_process.returncode}"
        )


def build(
    *, charm_name: str, build_dir: Path, install_dir: Path, charm_build_arguments: list[str]
):
    """Build a charm using charm tool.

    The charm tool is used to build reactive charms, the build process
    is as follows:

    - Run charm proof to ensure the charm
      would build with no errors (warnings are allowed)

    - Link charm tool's build directory to the part lifecycle's
      install_dir

    - Run "charm build"

    Note that no files/dirs in the original project are modified nor removed
    because in that case the VCS will detect something changed and the version
    string produced by `charm` would be misleading.
    """
    # Verify the charm is ok from a charm tool point of view.

    try:
        run_charm_tool(["charm", "proof"])
    except subprocess.CalledProcessError as call_error:
        return call_error.returncode

    # Link the installation directory to the place where charm creates
    # the charm.
    charm_build_dir = build_dir / charm_name
    if not charm_build_dir.exists():
        charm_build_dir.symlink_to(install_dir, target_is_directory=True)

    cmd = ["charm", "build"]
    if charm_build_arguments:
        cmd.extend(charm_build_arguments)
    cmd.extend(["-o", str(build_dir)])

    try:
        run_charm_tool(cmd)
    except subprocess.CalledProcessError as call_error:
        return call_error.returncode
    finally:
        charm_build_dir.unlink()

    return 0


if __name__ == "__main__":
    returncode = build(
        charm_name=sys.argv[1],
        build_dir=Path(sys.argv[2]),
        install_dir=Path(sys.argv[3]),
        charm_build_arguments=sys.argv[4:],
    )
    sys.exit(returncode)
