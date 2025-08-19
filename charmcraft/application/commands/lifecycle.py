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
"""craft-application based lifecycle commands."""

from __future__ import annotations

import pathlib
import textwrap
from typing import TYPE_CHECKING, Any, cast

import craft_cli
from craft_application.commands import lifecycle
from craft_application.util import is_managed_mode
from craft_cli import CraftError
from typing_extensions import override

from charmcraft import models, utils

if TYPE_CHECKING:  # pragma: no cover
    import argparse

    from charmcraft.services.charmlibs import CharmLibsService
    from charmcraft.services.store import StoreService


def get_lifecycle_commands() -> list[type[craft_cli.BaseCommand]]:
    """Return the lifecycle related command group."""
    return [
        lifecycle.CleanCommand,
        lifecycle.PullCommand,
        lifecycle.BuildCommand,
        lifecycle.StageCommand,
        lifecycle.PrimeCommand,
        PackCommand,
        lifecycle.TestCommand,
    ]


class PackCommand(lifecycle.PackCommand):
    """Command to pack the final artifact."""

    name = "pack"
    help_msg = "Build the charm"
    overview = textwrap.dedent(
        """
        Build and pack a charm operator.

        You can `juju deploy` the resulting `.charm` file directly, or
        upload it to Charmhub with `charmcraft upload`.

        For the charm you must be inside a charm directory with a valid
        `metadata.yaml`, `requirements.txt` including the `ops` package
        for the Python operator framework, and an operator entrypoint,
        usually `src/charm.py`.  See `charmcraft init` to create a
        template charm directory structure.
        """
    )

    @override
    def _fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super()._fill_parser(parser)

        parser.add_argument(
            "--bases-index",
            action="append",
            type=int,
            help="Index of 'bases' configuration to build (can be used multiple "
            "times); zero-based, defaults to all",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force packing even after finding lint errors",
        )
        parser.add_argument(
            "--measure",
            type=pathlib.Path,
            help="Dump measurements to the specified file",
        )
        parser.add_argument(
            "--format",
            choices=["json"],
            help="Produce a machine-readable format (currently only json)",
        )
        parser.add_argument(
            "--project-dir",
            "-p",
            type=pathlib.Path,
            default=pathlib.Path.cwd(),
            help="Specify the project's directory (defaults to current)",
        )

    @override
    @staticmethod
    def _should_add_shell_args() -> bool:
        return True

    def _validate_bases_indices(self, bases_indices):
        """Validate that bases index is valid."""
        if bases_indices is None:
            return

        project = cast(models.Charm, self._services.project)

        msg = "Bases index '{}' is invalid (must be >= 0 and fit in configured bases)."
        len_configured_bases = len(project.bases)
        for bases_index in bases_indices:
            if bases_index < 0:
                raise CraftError(msg.format(bases_index))
            if bases_index >= len_configured_bases:
                raise CraftError(msg.format(bases_index))

    def _update_charm_libs(self) -> None:
        """Update charm libs attached to the project."""
        craft_cli.emit.progress(
            "Checking that charmlibs match 'charmcraft.yaml' values"
        )
        project = cast(models.CharmcraftProject, self._services.get("project").get())
        libs_svc = cast("CharmLibsService", self._services.get("charm_libs"))
        installable_libs: list[models.CharmLib] = []
        for lib in project.charm_libs:
            library_name = utils.QualifiedLibraryName.from_string(lib.lib)
            if not libs_svc.get_local_version(
                charm_name=library_name.charm_name, lib_name=library_name.lib_name
            ):
                installable_libs.append(lib)
        if installable_libs:
            store = cast("StoreService", self._services.store)
            libraries_md = store.get_libraries_metadata(installable_libs)
            with craft_cli.emit.progress_bar(
                "Downloading charmlibs...", len(installable_libs)
            ) as progress:
                for library in libraries_md:
                    craft_cli.emit.debug(repr(library))
                    lib_contents = store.get_library(
                        library.charm_name,
                        library_id=library.lib_id,
                        api=library.api,
                        patch=library.patch,
                    )
                    libs_svc.write(lib_contents)
                    progress.advance(1)

    def _run(
        self,
        parsed_args: argparse.Namespace,
        step_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        project = cast(models.CharmcraftProject, self._services.get("project").get())
        if project.charm_libs:
            self._update_charm_libs()

        result = super()._run(parsed_args, step_name, **kwargs)

        # Move artifacts in the outer instance.
        if not is_managed_mode():
            state_service = self._services.get("state")
            try:
                artifacts = cast(dict[str, pathlib.Path], state_service.get("artifact"))
            except KeyError:
                craft_cli.emit.debug(
                    "Could not find artifacts in the state service. Not moving."
                )
            else:
                project_dir = parsed_args.project_dir or pathlib.Path.cwd()
                output_dir = parsed_args.output or pathlib.Path.cwd()

                for artifact in artifacts.values():
                    old_path = project_dir / artifact
                    new_path = output_dir / artifact
                    if old_path != new_path:
                        old_path.rename(new_path)

        return result
