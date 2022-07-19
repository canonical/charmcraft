# Copyright 2021-2022 Canonical Ltd.
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

import os
import pathlib
import shlex
import sys
from typing import Any, Dict, List, Set, cast

import pydantic
from craft_cli import emit, CraftError
from craft_parts import LifecycleManager, Step, plugins
from craft_parts.errors import PartsError
from craft_parts.parts import PartSpec
from xdg import BaseDirectory  # type: ignore

from charmcraft import charm_builder
from charmcraft.reactive_plugin import ReactivePlugin


class CharmPluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """Properties used in charm building."""

    source: str
    charm_entrypoint: str = "src/charm.py"
    charm_binary_python_packages: List[str] = []
    charm_python_packages: List[str] = []
    charm_requirements: List[str] = []

    @pydantic.validator("charm_entrypoint")
    def validate_entry_point(cls, charm_entrypoint, values):
        """Validate the entry point."""
        # the location of the project is needed
        if "source" not in values:
            raise ValueError(
                "cannot validate 'charm-entrypoint' because invalid 'source' configuration"
            )
        project_dirpath = pathlib.Path(values["source"]).resolve()

        # check that the entrypoint is inside the project
        filepath = (project_dirpath / charm_entrypoint).resolve()
        if project_dirpath not in filepath.parents:
            raise ValueError(
                "charm entry point must be inside the project: {!r}".format(str(filepath))
            )

        # store the entrypoint always relative to the project's path (no matter if the origin
        # was relative or absolute)
        rel_entrypoint = (project_dirpath / charm_entrypoint).relative_to(project_dirpath)
        charm_entrypoint = rel_entrypoint.as_posix()

        return charm_entrypoint

    @pydantic.validator("charm_requirements", always=True)
    def validate_requirements(cls, charm_requirements, values):
        """Validate the specified requirement or dynamically default it.

        The default is dynamic because it's only requirements.txt if the
        file is there.
        """
        # the location of the project is needed
        if "source" not in values:
            raise ValueError(
                "cannot validate 'charm-requirements' because invalid 'source' configuration"
            )
        project_dirpath = pathlib.Path(values["source"])

        # check that all indicated files are present
        for reqs_filename in charm_requirements:
            reqs_path = project_dirpath / reqs_filename
            if not reqs_path.is_file():
                raise ValueError(f"requirements file {str(reqs_path)!r} not found")

        # if nothing indicated, and default file is there, use it
        default_reqs_name = "requirements.txt"
        if not charm_requirements and (project_dirpath / default_reqs_name).is_file():
            charm_requirements.append(default_reqs_name)

        return charm_requirements

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
        return {
            "python3-pip",
            "python3-setuptools",
            "python3-wheel",
            "python3-venv",
            "python3-dev",
        }

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(CharmPluginProperties, self._options)

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

        if options.charm_entrypoint:
            entrypoint = self._part_info.part_build_dir / options.charm_entrypoint
            build_cmd.extend(["--entrypoint", str(entrypoint)])

        for pkg in options.charm_binary_python_packages:
            build_cmd.extend(["-b", pkg])

        for pkg in options.charm_python_packages:
            build_cmd.extend(["-p", pkg])

        for req in options.charm_requirements:
            build_cmd.extend(["-r", req])

        commands = [" ".join(shlex.quote(i) for i in build_cmd)]

        return commands


class BundlePluginProperties(plugins.PluginProperties, plugins.PluginModel):
    """Properties used to pack bundles."""

    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate bundle properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = plugins.extract_plugin_properties(
            data, plugin_name="bundle", required=["source"]
        )
        return cls(**plugin_data)


class BundlePlugin(plugins.Plugin):
    """Prepare a bundle for packing.

    Extra files to be included in the bundle payload must be listed under
    the ``prime`` file filter.
    """

    properties_class = BundlePluginProperties

    @classmethod
    def get_build_snaps(cls) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        install_dir = self._part_info.part_install_dir
        if sys.platform == "linux":
            cp_cmd = "cp --archive --link --no-dereference"
        else:
            cp_cmd = "cp -R -p -P"

        commands = [
            'mkdir -p "{}"'.format(install_dir),
            '{} * "{}"'.format(cp_cmd, install_dir),
        ]
        return commands


def setup_parts():
    """Initialize craft-parts plugins."""
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})


def process_part_config(data: Dict[str, Any]) -> None:
    """Validate and fill the given part data against/with common and plugin models.

    :param data: The part data to use.

    :return: The part data validated and completed with plugin defaults.
    """
    if not isinstance(data, dict):
        raise TypeError("value must be a dictionary")

    # copy the original data, we'll modify it
    spec = data.copy()

    plugin_name = spec.get("plugin")
    if not plugin_name:
        raise ValueError("'plugin' not defined")

    plugin_class = plugins.get_plugin_class(plugin_name)

    # validate plugin properties
    plugin_properties = plugin_class.properties_class.unmarshal(spec)

    # validate common part properties
    part_spec = plugins.extract_part_properties(spec, plugin_name=plugin_name)
    PartSpec(**part_spec)

    # get plugin properties data if it's model based (otherwise it's empty), and
    # update with the received config
    if isinstance(plugin_properties, plugins.PluginModel):
        full_config = plugin_properties.dict(by_alias=True)
    else:
        full_config = {}
    full_config.update(data)

    return full_config


class PartsLifecycle:
    """Create and manage the parts lifecycle.

    :param all_parts: A dictionary containing the parts defined in the project.
    :param work_dir: The working directory for parts processing.
    :param project_dir: The directory containing the charm project.
    :param ignore_local_sources: A list of local source patterns to be ignored.
    :param name: Charm name as defined in ``metadata.yaml``.
    """

    def __init__(
        self,
        all_parts: Dict[str, Any],
        *,
        work_dir: pathlib.Path,
        project_dir: pathlib.Path,
        project_name: str,
        ignore_local_sources: List[str],
    ):
        self._all_parts = all_parts.copy()
        self._project_dir = project_dir

        # set the cache dir for parts package management
        cache_dir = BaseDirectory.save_cache_path("charmcraft")

        try:
            self._lcm = LifecycleManager(
                {"parts": all_parts},
                application_name="charmcraft",
                work_dir=work_dir,
                cache_dir=cache_dir,
                ignore_local_sources=ignore_local_sources,
                project_name=project_name,
            )
        except PartsError as err:
            raise CraftError(f"Error bootstrapping lifecycle manager: {err}") from err

    @property
    def prime_dir(self) -> pathlib.Path:
        """Return the parts prime directory path."""
        return self._lcm.project_info.prime_dir

    def run(self, target_step: Step) -> None:
        """Run the parts lifecycle.

        :param target_step: The final step to execute.

        :raises CraftError: On error during lifecycle ops.
        :raises RuntimeError: On unexpected error.
        """
        previous_dir = os.getcwd()
        try:
            os.chdir(self._project_dir)

            # invalidate build if packing a charm and entrypoint changed
            if "charm" in self._all_parts:
                charm_part = self._all_parts["charm"]
                if charm_part.get("plugin") == "charm":
                    entrypoint = os.path.normpath(charm_part["charm-entrypoint"])
                    dis_entrypoint = os.path.normpath(_get_dispatch_entrypoint(self.prime_dir))
                    if entrypoint != dis_entrypoint:
                        self._lcm.clean(Step.BUILD, part_names=["charm"])
                        self._lcm.reload_state()

            emit.debug(f"Executing parts lifecycle in {str(self._project_dir)!r}")
            actions = self._lcm.plan(target_step)
            emit.debug(f"Parts actions: {actions}")
            with self._lcm.action_executor() as aex:
                for action in actions:
                    emit.progress(f"Running step {action.step.name} for part {action.part_name!r}")
                    with emit.open_stream("Execute action") as stream:
                        aex.execute([action], stdout=stream, stderr=stream)
        except RuntimeError as err:
            raise RuntimeError(f"Parts processing internal error: {err}") from err
        except OSError as err:
            msg = err.strerror
            if err.filename:
                msg = f"{err.filename}: {msg}"
            raise CraftError(f"Parts processing error: {msg}") from err
        except Exception as err:
            raise CraftError(f"Parts processing error: {err}") from err
        finally:
            os.chdir(previous_dir)


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
