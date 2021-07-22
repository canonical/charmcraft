# Copyright 2021 Canonical Ltd.
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

"""Craft-parts setup, lifecycle and plugins."""

import logging
import os
import pathlib
import shlex
import sys
from typing import Any, Dict, List, Set

from craft_parts import LifecycleManager, Step, plugins
from craft_parts.parts import PartSpec
from craft_parts.errors import PartsError
from xdg import BaseDirectory  # type: ignore

from charmcraft import charm_builder
from charmcraft.cmdbase import CommandError

logger = logging.getLogger(__name__)


class CharmPluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """Properties used in charm building."""

    source: str = ""
    # TODO: add charm plugin properties

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate charm properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = plugins.extract_plugin_properties(
            data, plugin_name="charm", required=["source"]
        )
        return cls(**plugin_data)


class CharmPlugin(plugins.Plugin):
    """Build the charm and prepare for packing.

    The craft-parts charm plugin prepares the charm payload for packing. Common
    plugin and source keywords can be used.

    Extra files to be included in the charm payload must be listed under
    the ``prime`` file filter.
    """

    properties_class = CharmPluginProperties

    @classmethod
    def get_build_snaps(cls) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {}

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        build_env = dict(LANG="C.UTF-8", LC_ALL="C.UTF-8")
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

        env_flags = [f"{key}={value}" for key, value in build_env.items()]

        # invoke the charm builder
        build_cmd = [
            "env",
            "-i",
            *env_flags,
            sys.executable,
            "-I",
            charm_builder.__file__,
            "--charmdir",
            str(self._part_info.part_build_dir),
            "--builddir",
            str(self._part_info.part_install_dir),
        ]

        if self._part_info.entrypoint:
            entrypoint = self._part_info.part_build_dir / self._part_info.entrypoint
            build_cmd.extend(["--entrypoint", str(entrypoint)])

        for req in self._part_info.requirements:
            build_cmd.extend(["-r", req])

        commands = [" ".join(shlex.quote(i) for i in build_cmd)]

        return commands


def setup_parts():
    """Initialize craft-parts plugins."""
    plugins.register({"charm": CharmPlugin})


def validate_part(data: Dict[str, Any]) -> None:
    """Validate the given part data against common and plugin models.

    :param data: The part data to validate.
    """
    if not isinstance(data, dict):
        raise TypeError("value must be a dictionary")

    # copy the original data, we'll modify it
    spec = data.copy()

    plugin_name = spec.get("plugin", "")
    if not plugin_name:
        raise ValueError("'plugin' not defined")

    plugin_class = plugins.get_plugin_class(plugin_name)

    # validate plugin properties
    plugin_class.properties_class.unmarshal(spec)

    # validate common part properties
    plugins.strip_plugin_properties(spec, plugin_name=plugin_name)
    PartSpec(**spec)


class PartsLifecycle:
    """Create and manage the parts lifecycle."""

    def __init__(
        self,
        all_parts: Dict[str, Any],
        *,
        work_dir: pathlib.Path,
        entrypoint: pathlib.Path,
        requirements: List[pathlib.Path],
    ):
        self._all_parts = all_parts

        # set the cache dir for parts package management
        cache_dir = BaseDirectory.save_cache_path("charmcraft")

        try:
            self._lcm = LifecycleManager(
                {"parts": all_parts},
                application_name="charmcraft",
                work_dir=work_dir,
                cache_dir=cache_dir,
                ignore_local_sources=["*.charm"],
                entrypoint=entrypoint,
                requirements=requirements,
            )
            self._lcm.refresh_packages_list()
        except PartsError as err:
            raise CommandError(err)

    @property
    def prime_dir(self) -> pathlib.Path:
        """Return the parts prime directory path."""
        return self._lcm.project_info.prime_dir

    def run(self, target_step: Step) -> None:
        """Run the parts lifecycle.

        :param target_step: The final step to execute.
        """
        try:
            # invalidate build if packing a charm and entrypoint changed
            if "charm" in self._all_parts:
                entrypoint = os.path.normpath(self._lcm.project_info.entrypoint)
                dis_entrypoint = os.path.normpath(
                    _get_dispatch_entrypoint(self.prime_dir)
                )
                if entrypoint != dis_entrypoint:
                    self._lcm.clean(Step.BUILD, part_names=["charm"])
                    self._lcm.reload_state()

            actions = self._lcm.plan(target_step)
            logger.debug("Parts actions: %s", actions)
            with self._lcm.action_executor() as aex:
                aex.execute(actions)
        except RuntimeError as err:
            raise RuntimeError(f"Parts processing internal error: {err}") from err
        except OSError as err:
            msg = err.strerror
            if err.filename:
                msg = f"{err.filename}: {msg}"
            raise CommandError(f"Parts processing error: {msg}") from err
        except Exception as err:
            raise CommandError(f"Parts processing error: {err}") from err


def _get_dispatch_entrypoint(dirname: pathlib.Path) -> str:
    """Read the entrypoint from the dispatch file."""
    dispatch = dirname / charm_builder.DISPATCH_FILENAME
    entrypoint_str = ""
    try:
        with dispatch.open("rt", encoding="utf8") as fh:
            last_line = None
            for line in fh:
                if line.strip():
                    last_line = line
            if last_line:
                entrypoint_str = shlex.split(last_line)[-1]
    except (IOError, UnicodeDecodeError):
        return ""

    return entrypoint_str
