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

import os
import pathlib
import subprocess
import textwrap
from typing import TYPE_CHECKING

import craft_cli
from craft_cli import ArgumentParsingError, CraftError, emit
from typing_extensions import override

from charmcraft import utils
from charmcraft.application.commands.base import CharmcraftCommand

if TYPE_CHECKING:  # pragma: no cover
    import argparse

BUNDLE_MANDATORY_FILES = ["bundle.yaml", "README.md"]


def get_lifecycle_commands() -> list[type[craft_cli.BaseCommand]]:
    """Return the lifecycle related command group."""
    return [
        CleanCommand,
        PullCommand,
        BuildCommand,
        StageCommand,
        PrimeCommand,
        PackCommand,
    ]


class _LifecycleCommand(CharmcraftCommand):
    """Lifecycle-related commands."""

    @override
    def run(self, parsed_args: argparse.Namespace) -> None:
        emit.trace(f"lifecycle command: {self.name!r}, arguments: {parsed_args!r}")


class _LifecyclePartsCommand(_LifecycleCommand):
    # All lifecycle-related commands need a project to work
    always_load_project = True

    @override
    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)  # type: ignore[arg-type]
        parser.add_argument(
            "parts",
            metavar="part-name",
            type=str,
            nargs="*",
            help="Optional list of parts to process",
        )
        parser.add_argument(
            "--destructive-mode",
            action="store_true",
            help="Build in the current host",
        )

    @override
    def get_managed_cmd(self, parsed_args: argparse.Namespace) -> list[str]:
        cmd = super().get_managed_cmd(parsed_args)

        cmd.extend(parsed_args.parts)

        return cmd


class _LifecycleStepCommand(_LifecyclePartsCommand):
    @override
    def run_managed(self, parsed_args: argparse.Namespace) -> bool:
        return not parsed_args.destructive_mode

    @override
    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)

        if self._should_add_shell_args():
            group = parser.add_mutually_exclusive_group()
            group.add_argument(
                "--shell",
                action="store_true",
                help="Shell into the environment in lieu of the step to run.",
            )
            group.add_argument(
                "--shell-after",
                action="store_true",
                help="Shell into the environment after the step has run.",
            )

        parser.add_argument(
            "--debug",
            action="store_true",
            help="Shell into the environment if the build fails.",
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--platform",
            type=str,
            metavar="name",
            default=os.getenv("CRAFT_PLATFORM"),
            help="Set platform to build for",
        )
        group.add_argument(
            "--build-for",
            type=str,
            metavar="arch",
            default=os.getenv("CRAFT_BUILD_FOR"),
            help="Set architecture to build for",
        )

    @override
    def get_managed_cmd(self, parsed_args: argparse.Namespace) -> list[str]:
        """Get the command to run in managed mode.

        :param parsed_args: The parsed arguments used.
        :returns: A list of strings ready to be passed into a craft-providers executor.
        :raises: RuntimeError if this command is not supposed to run managed.
        """
        cmd = super().get_managed_cmd(parsed_args)

        if getattr(parsed_args, "shell", False):
            cmd.append("--shell")
        if getattr(parsed_args, "shell_after", False):
            cmd.append("--shell-after")

        return cmd

    @override
    def run(self, parsed_args: argparse.Namespace, step_name: str | None = None) -> None:
        """Run a lifecycle step command."""
        super().run(parsed_args)

        shell = getattr(parsed_args, "shell", False)
        shell_after = getattr(parsed_args, "shell_after", False)
        debug = getattr(parsed_args, "debug", False)

        step_name = step_name or self.name

        if shell:
            previous_step = self._services.lifecycle.previous_step_name(step_name)
            step_name = previous_step
            shell_after = True

        try:
            self._services.lifecycle.run(
                step_name=step_name,
                part_names=parsed_args.parts,
            )
        except Exception as err:
            if debug:
                emit.progress(str(err), permanent=True)
                _launch_shell()
            raise

        if shell_after:
            _launch_shell()

    @staticmethod
    def _should_add_shell_args() -> bool:
        return True


class PullCommand(_LifecycleStepCommand):
    """Command to pull parts."""

    name = "pull"
    help_msg = "Download or retrieve artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Download or retrieve artifacts defined for a part. If part names
        are specified only those parts will be pulled, otherwise all parts
        will be pulled.
        """
    )


class BuildCommand(_LifecycleStepCommand):
    """Command to build parts."""

    name = "build"
    help_msg = "Build artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Build artifacts defined for a part. If part names are specified only
        those parts will be built, otherwise all parts will be built.
        """
    )


class StageCommand(_LifecycleStepCommand):
    """Command to stage parts."""

    name = "stage"
    help_msg = "Stage built artifacts into a common staging area"
    overview = textwrap.dedent(
        """
        Stage built artifacts into a common staging area. If part names are
        specified only those parts will be staged. The default is to stage
        all parts.
        """
    )


class PrimeCommand(_LifecycleStepCommand):
    """Command to prime parts."""

    name = "prime"
    help_msg = "Prime artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Prepare the final payload to be packed, performing additional
        processing and adding metadata files. If part names are specified only
        those parts will be primed. The default is to prime all parts.
        """
    )

    @override
    def run(self, parsed_args: argparse.Namespace, step_name: str | None = None) -> None:
        """Run the prime command."""
        super().run(parsed_args, step_name=step_name)

        self._services.package.write_metadata(self._services.lifecycle.prime_dir)


class PackCommand(PrimeCommand):
    """Command to pack the final artifact."""

    name = "pack"
    help_msg = "Build the charm or bundle"
    overview = textwrap.dedent(
        """
        Build and pack a charm operator package or a bundle.

        You can `juju deploy` the resulting `.charm` or bundle's `.zip`
        file directly, or upload it to Charmhub with `charmcraft upload`.

        For the charm you must be inside a charm directory with a valid
        `metadata.yaml`, `requirements.txt` including the `ops` package
        for the Python operator framework, and an operator entrypoint,
        usually `src/charm.py`.  See `charmcraft init` to create a
        template charm directory structure.

        For the bundle you must already have a `bundle.yaml` (can be
        generated by Juju) and a README.md file.
        """
    )

    @override
    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)

        parser.add_argument(
            "--output",
            "-o",
            type=pathlib.Path,
            default=pathlib.Path(),
            help="Output directory for created packages.",
        )
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
        include_charm_group = parser.add_mutually_exclusive_group()
        include_charm_group.add_argument(
            "--include-all-charms",
            action="store_true",
            help="For bundles, pack all charms whose source is inside the bundle directory",
        )
        include_charm_group.add_argument(
            "--include-charm",
            action="append",
            type=pathlib.Path,
            help="For bundles, pack the charm in the referenced path. Can be used multiple times",
        )
        parser.add_argument(
            "--output-bundle",
            type=pathlib.Path,
            help="Write the bundle configuration to this path",
        )
        parser.add_argument(
            "--format",
            choices=["json"],
            help="Produce a machine-readable format (currently only json)",
        )

    @override
    def run(self, parsed_args: argparse.Namespace, step_name: str | None = None) -> None:
        """Run the pack command."""
        self._validate_args(parsed_args)
        if step_name not in ("pack", None):
            raise RuntimeError(f"Step name {step_name} passed to pack command.")
        super().run(parsed_args, step_name="prime")

        emit.progress("Packing...")
        packages = self._services.package.pack(
            self._services.lifecycle.prime_dir, parsed_args.output
        )

        if not packages:
            emit.message("No packages created.")
        elif len(packages) == 1:
            emit.message(f"Packed {packages[0].name}")
        else:
            package_names = ", ".join(pkg.name for pkg in packages)
            emit.message(f"Packed: {package_names}")

    @staticmethod
    @override
    def _should_add_shell_args() -> bool:
        return True

    def _validate_args(self, parsed_args: argparse.Namespace) -> None:
        if self._services.project.type == "charm":
            if parsed_args.include_all_charms:
                raise ArgumentParsingError(
                    "--include-all-charms can only be used when packing a bundle. "
                    f"Currently trying to pack: {self._services.package.project_dir}"
                )
            if parsed_args.include_charm:
                raise ArgumentParsingError(
                    "--include-charm can only be used when packing a bundle. "
                    f"Currently trying to pack: {self._services.package.project_dir}"
                )
            if parsed_args.output_bundle:
                raise ArgumentParsingError(
                    "--output-bundle can only be used when packing a bundle. "
                    f"Currently trying to pack: {self._services.package.project_dir}"
                )

    def _validate_bases_indices(self, bases_indices):
        """Validate that bases index is valid."""
        if bases_indices is None:
            return

        msg = "Bases index '{}' is invalid (must be >= 0 and fit in configured bases)."
        len_configured_bases = len(self._services.project.bases)
        for bases_index in bases_indices:
            if bases_index < 0:
                raise CraftError(msg.format(bases_index))
            if bases_index >= len_configured_bases:
                raise CraftError(msg.format(bases_index))

    def run_managed(self, parsed_args: argparse.Namespace) -> bool:
        """Whether to run this command in managed mode.

        If we're packing a bundle, run unmanaged. Otherwise, do what other lifecycle
        commands do.
        """
        charmcraft_yaml = utils.load_yaml(pathlib.Path("charmcraft.yaml"))
        if charmcraft_yaml and charmcraft_yaml.get("type") == "bundle":
            return False
        return super().run_managed(parsed_args)


class CleanCommand(_LifecyclePartsCommand):
    """Command to remove part assets."""

    name = "clean"
    help_msg = "Remove a part's assets"
    overview = textwrap.dedent(
        """
        Clean up artifacts belonging to parts. If no parts are specified,
        remove the packing environment.
        """
    )

    @override
    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the clean command."""
        super().run(parsed_args)

        if parsed_args.destructive_mode or not self._should_clean_instances(parsed_args):
            self._services.lifecycle.clean(parsed_args.parts)
        else:
            self._services.provider.clean_instances()

    @override
    def run_managed(self, parsed_args: argparse.Namespace) -> bool:
        if parsed_args.destructive_mode:
            # In destructive mode, always run on the host.
            return False

        # "clean" should run managed if cleaning specific parts.
        # otherwise, should run on the host to clean the build provider.
        return not self._should_clean_instances(parsed_args)

    @staticmethod
    def _should_clean_instances(parsed_args: argparse.Namespace) -> bool:
        return not bool(parsed_args.parts)


def _launch_shell() -> None:
    """Launch a user shell for debugging environment."""
    emit.progress("Launching shell on build environment...", permanent=True)
    with emit.pause():
        subprocess.run(["bash"], check=False)
