# Copyright 2023 Canonical Ltd.
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
"""Lifecycle class for craft-parts.

PENDING DEPRECATION: we're moving this to a craft-application LifecycleService
"""

import os
import pathlib
import shlex
from typing import Any

from craft_cli import CraftError, emit
from craft_parts import LifecycleManager, PartsError, Step
from xdg import BaseDirectory  # type: ignore[import]

from charmcraft import const, instrum


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
        all_parts: dict[str, Any],
        *,
        work_dir: pathlib.Path,
        project_dir: pathlib.Path,
        project_name: str,
        ignore_local_sources: list[str],
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
                    dis_entrypoint = os.path.normpath(
                        _get_dispatch_entrypoint(self.prime_dir)
                    )
                    if entrypoint != dis_entrypoint:
                        self._lcm.clean(Step.BUILD, part_names=["charm"])
                        self._lcm.reload_state()

            # Workaround for https://github.com/canonical/craft-parts/issues/851:
            # craft-parts' local source update copies new/modified files but does
            # not remove files deleted from the source directory. Clean the pull
            # step for any affected part so stale files are not included in the
            # repacked charm archive.
            self._clean_stale_parts()

            emit.debug(f"Executing parts lifecycle in {str(self._project_dir)!r}")
            actions = self._lcm.plan(target_step)
            emit.debug(f"Parts actions: {actions}")
            with instrum.Timer("Running action executor") as executor_timer:
                with self._lcm.action_executor() as aex:
                    executor_timer.mark("Context enter")
                    for act in actions:
                        emit.progress(
                            f"Running step {act.step.name} for part {act.part_name!r}"
                        )
                        with instrum.Timer(
                            "Running step",
                            step=act.step.name,  # type: ignore[arg-type]
                            part=act.part_name,  # type: ignore[arg-type]
                        ):
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

    def _clean_stale_parts(self) -> None:
        """Clean parts whose local source has had files deleted since the last pull.

        Craft-parts' local source ``update()`` copies new/modified files but does
        not remove files from the part src directory that have been deleted from
        the original source. This method detects such deletions and triggers a
        clean pull for the affected parts so stale files are not included in the
        repacked charm archive.

        Workaround for https://github.com/canonical/craft-parts/issues/851.
        """
        parts_dir = self._lcm.project_info.dirs.parts_dir
        parts_to_clean: list[str] = []

        for part_name, part_spec in self._all_parts.items():
            source = part_spec.get("source", "")
            if not source:
                continue

            source_path = pathlib.Path(source)
            if not source_path.is_absolute():
                source_path = self._project_dir / source_path

            source_subdir = part_spec.get("source-subdir", "")
            if source_subdir:
                source_path = source_path / source_subdir

            if not source_path.is_dir():
                continue

            part_src_dir = parts_dir / part_name / "src"
            if not part_src_dir.exists():
                continue

            src_files = {
                f.relative_to(part_src_dir)
                for f in part_src_dir.rglob("*")
                if f.is_file()
            }
            source_files = {
                f.relative_to(source_path)
                for f in source_path.rglob("*")
                if f.is_file()
            }

            if src_files - source_files:
                emit.debug(
                    f"Source files deleted from part {part_name!r}; "
                    "cleaning to remove stale files from stage and prime."
                )
                parts_to_clean.append(part_name)

        if parts_to_clean:
            for part_name in parts_to_clean:
                self._lcm.clean(Step.PULL, part_names=[part_name])
            self._lcm.reload_state()


def _get_dispatch_entrypoint(dirname: pathlib.Path) -> str:
    """Read the entrypoint from the dispatch file."""
    dispatch = dirname / const.DISPATCH_FILENAME
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
