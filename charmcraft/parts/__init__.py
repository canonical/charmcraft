# Copyright 2021-2023 Canonical Ltd.
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
from typing import Any, Dict, List

from craft_cli import CraftError, emit
from craft_parts import LifecycleManager, Step, plugins
from craft_parts.errors import PartsError
from craft_parts.parts import PartSpec
from xdg import BaseDirectory  # type: ignore

from charmcraft import charm_builder, instrum
from charmcraft.parts.bundle import BundlePlugin
from charmcraft.parts.charm import CharmPlugin, CharmPluginProperties
from charmcraft.reactive_plugin import ReactivePlugin, ReactivePluginProperties

__all__ = [
    "CharmPlugin",
    "CharmPluginProperties",
    "ReactivePlugin",
    "ReactivePluginProperties",
    "setup_parts",
    "process_part_config",
    "PartsLifecycle",
]


def setup_parts():
    """Initialize craft-parts plugins."""
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})


def process_part_config(data: Dict[str, Any]) -> Dict[str, Any]:
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
            with instrum.Timer("Running action executor") as executor_timer:
                with self._lcm.action_executor() as aex:
                    executor_timer.mark("Context enter")
                    for act in actions:
                        emit.progress(f"Running step {act.step.name} for part {act.part_name!r}")
                        with instrum.Timer("Running step", step=act.step.name, part=act.part_name):  # type: ignore[arg-type]
                            with emit.open_stream("Execute action") as stream:
                                aex.execute([act], stdout=stream, stderr=stream)
                    executor_timer.mark("Context exit")

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
    except (OSError, UnicodeDecodeError):
        return ""

    return entrypoint_str
