# Copyright 2023-2024 Canonical Ltd.
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
"""Charm plugin for craft-parts."""
import os
import pathlib
import re
import shlex
import sys
from contextlib import suppress
from typing import Literal, cast

import overrides
import pydantic
from craft_parts import Step, callbacks, plugins
from craft_parts.errors import OsReleaseIdError, OsReleaseVersionIdError
from craft_parts.packages import platform
from craft_parts.utils import os_utils
from typing_extensions import Self

from charmcraft import charm_builder, env, instrum

PACKAGE_NAME_REGEX = re.compile(r"[A-Za-z0-9_.-]+")


class CharmPluginProperties(plugins.PluginProperties, frozen=True):
    """Properties used in charm building."""

    plugin: Literal["charm"] = "charm"
    source: str = "."
    charm_entrypoint: str = "src/charm.py"
    charm_binary_python_packages: list[str] = []
    charm_python_packages: list[str] = []
    charm_requirements: list[str] = []
    charm_strict_dependencies: bool = False
    """Whether to select strict dependencies only.

    If true, ``charm-strict-dependencies`` will enforce that all dependencies, direct or indirect,
    be specified within a requirements file. This includes any ``PYDEPS`` specified from a charm
    library. It also changes the behaviour of ``charm-binary-python-packages`` to be a list of
    packages to pass to ``pip`` that are allowed to use binary packages.
    ``charm-strict-dependencies`` is mutually exclusive with ``charm-python-packages``.
    """

    @pydantic.field_validator("charm_entrypoint", mode="after")
    def _validate_entrypoint(cls, charm_entrypoint: str, info: pydantic.ValidationInfo) -> str:
        """Validate the entry point."""
        # the location of the project is needed
        if "source" not in info.data:
            raise ValueError(
                "cannot validate 'charm-entrypoint' because invalid 'source' configuration"
            )
        project_dirpath = pathlib.Path(info.data["source"]).resolve()

        # check that the entrypoint is inside the project
        filepath = (project_dirpath / charm_entrypoint).resolve()
        if project_dirpath not in filepath.parents:
            raise ValueError(f"charm entry point must be inside the project: {str(filepath)!r}")

        # store the entrypoint always relative to the project's path (no matter if the origin
        # was relative or absolute)
        rel_entrypoint = (project_dirpath / charm_entrypoint).relative_to(project_dirpath)
        return rel_entrypoint.as_posix()

    @pydantic.model_validator(mode="after")
    def _validate_requirements(self) -> Self:
        """Validate the specified requirement or dynamically default it.

        The default is dynamic because it's only requirements.txt if the
        file is there.
        """
        # the location of the project is needed
        if not self.source:
            raise ValueError(
                "cannot validate 'charm-requirements' because no 'source' was provided"
            )
        project_dirpath = pathlib.Path(self.source)

        # if nothing indicated, and default file is there, use it
        default_reqs_name = "requirements.txt"
        if not self.charm_requirements and (project_dirpath / default_reqs_name).is_file():
            self.charm_requirements.append(default_reqs_name)

        return self

    @pydantic.model_validator(mode="after")
    def _validate_strict_dependencies(self) -> Self:
        """Validate basic requirements if strict dependencies are enabled.

        Full validation that the requirements file contains all dependencies is done later, but
        we can fail early if the strict dependencies setting causes the charm to be invalid.
        """
        if not self.charm_strict_dependencies:
            return self

        if self.charm_python_packages:
            raise ValueError(
                "'charm-python-packages' must not be set if 'charm-strict-dependencies' is enabled"
            )

        if not self.charm_requirements:
            raise ValueError(
                "'charm-strict-dependencies' requires at least one requirements file."
            )

        invalid_binaries = set()
        for binary_package in self.charm_binary_python_packages:
            if not PACKAGE_NAME_REGEX.fullmatch(binary_package):
                invalid_binaries.add(binary_package)

        if invalid_binaries:
            raise ValueError(
                "'charm-binary-python-packages' may contain only package names allowed "
                "to be installed from binary if 'charm-strict-dependencies' is enabled. "
                f"Invalid package names: {sorted(invalid_binaries)}"
            )

        return self


class CharmPlugin(plugins.Plugin):
    """Build the charm and prepare for packing.

    The craft-parts charm plugin prepares the charm payload for packing. Common
    plugin and source keywords can be used, as well as the following optional
    plugin-specific properties:

      - ``charm-entrypoint``
        (string)
        The path to the main charm executable, relative to the charm root.

      - ``charm-binary-python-packages``
        (list of strings)
        A list of python packages to install from PyPI before installing
        requirements. Binary packages are allowed, but they may also be
        installed from sources if a package is only available in source form.

      - ``charm-python-packages``
        (list of strings)
        A list of python packages to install from PyPI before installing
        requirements. These packages will be installed from sources and built
        locally at packing time.

      - ``charm-requirements``
        (list of strings)
        List of paths to requirements files.

      - ``charm-strict-dependencies``
        (boolean)
        Whether to use legacy dependency resolution or strict dependency resolution.
        By default, legacy dependency resolution is used. If set to true, strict
        dependency resolution will be used, requiring all dependencies, including
        library dependencies, to be defined in provided requirements files.

    Extra files to be included in the charm payload must use the ``dump`` plugin.
    """

    properties_class = CharmPluginProperties

    @overrides.override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        if platform.is_deb_based():
            return {
                "python3-dev",
                "python3-pip",
                "python3-setuptools",
                "python3-venv",
                "python3-wheel",
                "libyaml-dev",
            }
        elif platform.is_yum_based():
            try:
                os_release = os_utils.OsRelease()
                if (os_release.id(), os_release.version_id()) in (("centos", "7"), ("rhel", "7")):
                    # CentOS 7 Python 3.8 from SCL repo
                    return {
                        "autoconf",
                        "automake",
                        "gcc",
                        "gcc-c++",
                        "git",
                        "make",
                        "patch",
                        "rh-python38-python-devel",
                        "rh-python38-python-pip",
                        "rh-python38-python-setuptools",
                        "rh-python38-python-wheel",
                    }
            except (OsReleaseIdError, OsReleaseVersionIdError):
                pass

            return {
                "autoconf",
                "automake",
                "gcc",
                "gcc-c++",
                "git",
                "make",
                "patch",
                "python3-devel",
                "python3-pip",
                "python3-setuptools",
                "python3-wheel",
            }
        elif platform.is_dnf_based():
            return {
                "python3-devel",
            }
        else:
            return set()

    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        environment = {
            # Cryptography fails to load OpenSSL legacy provider in some circumstances.
            # Since we don't need the legacy provider, this works around that bug.
            "CRYPTOGRAPHY_OPENSSL_NO_LEGACY": "true"
        }
        os_special_paths = self._get_os_special_priority_paths()
        if os_special_paths:
            environment["PATH"] = os_special_paths + ":${PATH}"

        return environment

    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(CharmPluginProperties, self._options)

        build_env = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            # Cryptography fails to load OpenSSL legacy provider in some circumstances.
            # Since we don't need the legacy provider, this works around that bug.
            "CRYPTOGRAPHY_OPENSSL_NO_LEGACY": "true",
        }
        for key in [
            "PATH",
            "SNAP",
            "SNAP_ARCH",
            "SNAP_NAME",
            "SNAP_VERSION",
            "http_proxy",
            "https_proxy",
            "no_proxy",
        ]:
            if key in os.environ:
                build_env[key] = os.environ[key]

        os_special_paths = self._get_os_special_priority_paths()
        if os_special_paths:
            build_env["PATH"] = os_special_paths + ":" + build_env["PATH"]

        env_flags = [f"{key}={value}" for key, value in build_env.items()]

        # invoke the charm builder
        build_cmd = [
            "env",
            "-i",
            *env_flags,
            sys.executable,
            "-u",
            "-I",
            charm_builder.__file__,
            "--builddir",
            str(self._part_info.part_build_dir),
            "--installdir",
            str(self._part_info.part_install_dir),
        ]

        if options.charm_entrypoint:
            entrypoint = self._part_info.part_build_dir / options.charm_entrypoint
            build_cmd.extend(["--entrypoint", str(entrypoint)])

        if options.charm_strict_dependencies:
            build_cmd.extend(self._get_strict_dependencies_parameters())
        else:
            build_cmd.extend(self._get_legacy_dependencies_parameters())

        commands = [" ".join(shlex.quote(i) for i in build_cmd)]

        # hook a callback after the BUILD happened (to collect metrics left by charm builder)
        callbacks.register_post_step(self.post_build_callback, step_list=[Step.BUILD])

        return commands

    def _get_strict_dependencies_parameters(self) -> list[str]:
        """Get the parameters to pass to the charm builder if strict dependencies are enabled."""
        options = cast(CharmPluginProperties, self._options)
        return [
            "--strict-dependencies",
            *(f"--binary-package={package}" for package in options.charm_binary_python_packages),
            *(f"--requirement={reqs}" for reqs in options.charm_requirements),
        ]

    def _get_legacy_dependencies_parameters(self) -> list[str]:
        """Get the parameters to pass to the charm builder with strict dependencies disabled."""
        options = cast(CharmPluginProperties, self._options)
        parameters = []
        try:
            if options.charm_python_packages or options.charm_requirements:
                base_tools = ["pip", "setuptools", "wheel"]

                # remove base tools if defined in charm_python_packages
                for pkg in options.charm_python_packages:
                    pkg = re.split("[<=>]", pkg, maxsplit=1)[0].strip()
                    if pkg in base_tools:
                        base_tools.remove(pkg)

                os_release = os_utils.OsRelease()
                if (os_release.id(), os_release.version_id()) in (("centos", "7"), ("rhel", "7")):
                    # CentOS 7 compatibility, bootstrap base tools use binary packages
                    for pkg in base_tools:
                        parameters.extend(["-b", pkg])

                # build base tools from source
                for pkg in base_tools:
                    parameters.extend(["-p", pkg])
        except (OsReleaseIdError, OsReleaseVersionIdError):
            pass

        for pkg in options.charm_binary_python_packages:
            parameters.extend(["-b", pkg])

        for pkg in options.charm_python_packages:
            parameters.extend(["-p", pkg])

        for req in options.charm_requirements:
            parameters.extend(["-r", req])

        return parameters

    def post_build_callback(self, step_info):
        """Collect metrics left by charm_builder.py."""
        instrum.merge_from(env.get_charm_builder_metrics_path())

    def _get_os_special_priority_paths(self) -> str | None:
        """Return a str of PATH for special OS."""
        with suppress(OsReleaseIdError, OsReleaseVersionIdError):
            os_release = os_utils.OsRelease()
            if (os_release.id(), os_release.version_id()) in (("centos", "7"), ("rhel", "7")):
                # CentOS 7 Python 3.8 from SCL repo
                return "/opt/rh/rh-python38/root/usr/bin"

        return None
