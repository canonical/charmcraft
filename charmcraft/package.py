# Copyright 2020-2023 Canonical Ltd.
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
"""Infrastructure for the 'pack' command."""

import os
import pathlib
import subprocess
import zipfile
from typing import List, Optional

from craft_cli import emit, CraftError
from craft_providers.bases import get_base_alias

import charmcraft.env
import charmcraft.linters
import charmcraft.parts
import charmcraft.providers
import charmcraft.instrum
from charmcraft.metafiles.config import create_config_yaml
from charmcraft.metafiles.actions import create_actions_yaml
from charmcraft.metafiles.manifest import create_manifest
from charmcraft.const import (
    BUILD_DIRNAME,
    CHARM_FILES,
    CHARM_OPTIONAL,
    VENV_DIRNAME,
    UBUNTU_LTS_STABLE,
)
from charmcraft.metafiles.metadata import create_metadata_yaml
from charmcraft.commands.store.charmlibs import collect_charmlib_pydeps
from charmcraft.models.charmcraft import Base, BasesConfiguration
from charmcraft.parts import Step
from charmcraft.utils import get_host_architecture


def _format_run_on_base(base: Base) -> str:
    """Formulate charm string for base section."""
    return "-".join([base.name, base.channel, *base.architectures])


def _format_bases_config(bases_config: BasesConfiguration) -> str:
    """Formulate charm string for bases configuration section."""
    return "_".join([_format_run_on_base(r) for r in bases_config.run_on])


def format_charm_file_name(charm_name: str, bases_config: BasesConfiguration) -> str:
    """Formulate charm file name.

    :param charm_name: Name of charm.
    :param bases_config: Bases configuration for charm.

    :returns: File name string, including .charm extension.
    """
    return "_".join([charm_name, _format_bases_config(bases_config)]) + ".charm"


def launch_shell(*, cwd: Optional[pathlib.Path] = None) -> None:
    """Launch a user shell for debugging environment.

    :param cwd: Working directory to start user in.
    """
    with emit.pause():
        subprocess.run(["bash"], check=False, cwd=cwd)


class Builder:
    """The package builder."""

    def __init__(self, *, config, force, debug, shell, shell_after, measure):
        self.force_packing = force
        self.debug = debug
        self.shell = shell
        self.shell_after = shell_after
        self.measure = measure

        self.charmdir = config.project.dirpath
        self.buildpath = self.charmdir / BUILD_DIRNAME
        self.config = config
        self._parts = self.config.parts.copy()

        # a part named "charm" using plugin "charm" is special and has
        # predefined values set automatically.
        charm_part = self._parts.get("charm")
        if charm_part and charm_part.get("plugin") == "charm":
            self._special_charm_part = charm_part
        else:
            self._special_charm_part = None

        self.provider = charmcraft.providers.get_provider()

    def show_linting_results(self, linting_results):
        """Manage the linters results, show some in different conditions, decide if continue."""
        attribute_results = []
        lint_results_by_outcome = {}
        for result in linting_results:
            if result.result == charmcraft.linters.IGNORED:
                continue
            if result.check_type == charmcraft.linters.CheckType.attribute:
                attribute_results.append(result)
            else:
                lint_results_by_outcome.setdefault(result.result, []).append(result)

        # show attribute results
        for result in attribute_results:
            emit.verbose(
                f"Check result: {result.name} [{result.check_type}] {result.result} "
                f"({result.text}; see more at {result.url}).",
            )

        # show warnings (if any), then errors (if any)
        template = "- {0.name}: {0.text} ({0.url})"
        if charmcraft.linters.WARNINGS in lint_results_by_outcome:
            emit.progress("Lint Warnings:", permanent=True)
            for result in lint_results_by_outcome[charmcraft.linters.WARNINGS]:
                emit.progress(template.format(result), permanent=True)
        if charmcraft.linters.ERRORS in lint_results_by_outcome:
            emit.progress("Lint Errors:", permanent=True)
            for result in lint_results_by_outcome[charmcraft.linters.ERRORS]:
                emit.progress(template.format(result), permanent=True)
            if self.force_packing:
                emit.progress("Packing anyway as requested.", permanent=True)
            else:
                raise CraftError(
                    "Aborting due to lint errors (use --force to override).", retcode=2
                )

    def build_charm(self, bases_config: BasesConfiguration) -> str:
        """Build the charm.

        :param bases_config: Bases configuration to use for build.

        :returns: File name of charm.

        :raises CraftError: on lifecycle exception.
        :raises RuntimeError: on unexpected lifecycle exception.
        """
        if charmcraft.env.is_charmcraft_running_in_managed_mode():
            work_dir = charmcraft.env.get_managed_environment_home_path()
        else:
            work_dir = self.buildpath

        emit.progress(f"Building charm in {str(work_dir)!r}")

        if self._special_charm_part:
            # add charm files to the prime filter
            # XXX Facundo 2022-07-18: we need to move this also to the plugin config
            self._set_prime_filter()

        # run the parts lifecycle
        emit.debug(f"Parts definition: {self._parts}")
        lifecycle = charmcraft.parts.PartsLifecycle(
            self._parts,
            work_dir=work_dir,
            project_dir=self.charmdir,
            project_name=self.config.name,
            ignore_local_sources=["*.charm"],
        )
        with charmcraft.instrum.Timer("Lifecycle run"):
            lifecycle.run(Step.PRIME)

        # skip creation yaml files if using reactive, reactive will create them
        # in a incompatible way
        if self._parts.get("charm", {}).get("plugin", None) != "reactive":
            create_actions_yaml(lifecycle.prime_dir, self.config)
            create_config_yaml(lifecycle.prime_dir, self.config)
            create_metadata_yaml(lifecycle.prime_dir, self.config)

        # run linters and show the results
        linting_results = charmcraft.linters.analyze(self.config, lifecycle.prime_dir)
        self.show_linting_results(linting_results)

        create_manifest(
            lifecycle.prime_dir,
            self.config.project.started_at,
            bases_config,
            linting_results,
        )

        zipname = self.handle_package(lifecycle.prime_dir, bases_config)
        emit.progress(f"Created '{zipname}'.", permanent=True)
        return zipname

    def _set_prime_filter(self):
        """Add mandatory and optional charm files to the prime filter.

        The prime filter should contain:
        - The charm entry point, or the directory containing it if it's
          not directly in the project dir.
        - A set of mandatory charm files, including metadata.yaml, the
          dispatcher and the hooks directory.
        - A set of optional charm files.
        """
        charm_part_prime = self._special_charm_part.setdefault("prime", [])

        # add entrypoint
        entrypoint = pathlib.Path(self._special_charm_part["charm-entrypoint"])
        if str(entrypoint) == entrypoint.name:
            # the entry point is in the root of the project, just include it
            charm_part_prime.append(str(entrypoint))
        else:
            # the entry point is in a subdir, include the whole subtree
            charm_part_prime.append(str(entrypoint.parts[0]))

        # add venv if there are requirements
        charmlib_pydeps = collect_charmlib_pydeps(self.charmdir)
        if (
            self._special_charm_part.get("charm-requirements")
            or self._special_charm_part.get("charm-binary-python-packages")
            or self._special_charm_part.get("charm-python-packages")
            or charmlib_pydeps
        ):
            charm_part_prime.append(VENV_DIRNAME)

        # add mandatory and optional charm files
        charm_part_prime.extend(CHARM_FILES)
        for fn in CHARM_OPTIONAL:
            path = self.charmdir / fn
            if path.exists():
                charm_part_prime.append(fn)

    @charmcraft.instrum.Timer("Builder run")
    def run(
        self, bases_indices: Optional[List[int]] = None, destructive_mode: bool = False
    ) -> List[str]:
        """Run build process.

        In managed-mode or destructive-mode, build for each bases configuration
        which has a matching build-on to the host we are executing on.  Warn for
        each base configuration that is incompatible.  Error if unable to
        produce any builds for any bases configuration.

        :returns: List of charm files created.
        """
        charms: List[str] = []

        managed_mode = charmcraft.env.is_charmcraft_running_in_managed_mode()
        if not managed_mode and not destructive_mode:
            charmcraft.providers.ensure_provider_is_available(self.provider)

        build_plan = charmcraft.providers.create_build_plan(
            bases=self.config.bases,
            bases_indices=bases_indices,
            destructive_mode=destructive_mode,
            managed_mode=managed_mode,
            provider=self.provider,
        )
        if not build_plan:
            raise CraftError(
                "No suitable 'build-on' environment found in any 'bases' configuration."
            )

        charms = []
        for plan in build_plan:
            emit.debug(f"Building for 'bases[{plan.bases_index:d}][{plan.build_on_index:d}]'.")
            if managed_mode or destructive_mode:
                if self.shell:
                    # Execute shell in lieu of build.
                    launch_shell()
                    continue

                try:
                    with charmcraft.instrum.Timer("Building the charm"):
                        charm_name = self.build_charm(plan.bases_config)
                except (CraftError, RuntimeError) as error:
                    if self.debug:
                        emit.debug(f"Launching shell as charm building ended in error: {error}")
                        launch_shell()
                    raise

                if self.shell_after:
                    launch_shell()
            else:
                charm_name = self.pack_charm_in_instance(
                    bases_index=plan.bases_index,
                    build_on=plan.build_on,
                    build_on_index=plan.build_on_index,
                )
            charms.append(charm_name)

        return charms

    def pack_charm_in_instance(
        self, *, bases_index: int, build_on: Base, build_on_index: int
    ) -> str:
        """Pack instance in Charm."""
        charm_name = format_charm_file_name(self.config.name, self.config.bases[bases_index])

        # If building in project directory, use the project path as the working
        # directory. The output charms will be placed in the correct directory
        # without needing retrieval. If outputting to a directory other than the
        # charm project directory, we need to output the charm outside the
        # project directory and can retrieve it when complete.
        cwd = pathlib.Path.cwd()
        if cwd == self.charmdir:
            instance_output_dir = charmcraft.env.get_managed_environment_project_path()
            pull_charm = False
        else:
            instance_output_dir = charmcraft.env.get_managed_environment_home_path()
            pull_charm = True

        mode = emit.get_mode().name.lower()
        cmd = ["charmcraft", "pack", "--bases-index", str(bases_index), f"--verbosity={mode}"]

        if self.debug:
            cmd.append("--debug")

        if self.shell:
            cmd.append("--shell")

        if self.shell_after:
            cmd.append("--shell-after")

        if self.force_packing:
            cmd.append("--force")

        if self.measure:
            instance_metrics = charmcraft.env.get_managed_environment_metrics_path()
            cmd.append(f"--measure={str(instance_metrics)}")

        emit.progress(
            f"Launching environment to pack for base {build_on} "
            "(may take a while the first time but it's reusable)"
        )

        build_base_alias = get_base_alias((build_on.name, build_on.channel))
        instance_name = charmcraft.providers.get_instance_name(
            bases_index=bases_index,
            build_on_index=build_on_index,
            project_name=self.config.name,
            project_path=self.charmdir,
            target_arch=get_host_architecture(),
        )
        base_configuration = charmcraft.providers.get_base_configuration(
            alias=build_base_alias,
            instance_name=instance_name,
        )

        if build_on.name == "ubuntu":
            if build_on.channel in UBUNTU_LTS_STABLE:
                allow_unstable = False
            else:
                allow_unstable = True
                emit.message(
                    f"Warning: non-LTS Ubuntu releases {build_on.channel} are "
                    "intended for experimental use only."
                )
        else:
            allow_unstable = True
            emit.message(
                f"Warning: Base {build_on.name} {build_on.channel} daily image may be unstable."
            )

        with self.provider.launched_environment(
            project_name=self.config.name,
            project_path=self.charmdir,
            base_configuration=base_configuration,
            instance_name=instance_name,
            allow_unstable=allow_unstable,
        ) as instance:
            emit.debug("Mounting directory inside the instance")
            with charmcraft.instrum.Timer("Mounting directory"):
                instance.mount(
                    host_source=self.charmdir,
                    target=charmcraft.env.get_managed_environment_project_path(),
                )

            emit.progress("Packing the charm")
            emit.debug(f"Running {cmd}")
            try:
                with charmcraft.instrum.Timer("Execution inside instance"):
                    with emit.pause():
                        instance.execute_run(cmd, check=True, cwd=instance_output_dir)
                    if self.measure:
                        with instance.temporarily_pull_file(instance_metrics) as local_filepath:
                            charmcraft.instrum.merge_from(local_filepath)
            except subprocess.CalledProcessError as error:
                raise CraftError(
                    f"Failed to build charm for bases index '{bases_index}'."
                ) from error
            finally:
                charmcraft.providers.capture_logs_from_instance(instance)

            if pull_charm:
                try:
                    instance.pull_file(
                        source=instance_output_dir / charm_name,
                        destination=cwd / charm_name,
                    )
                except FileNotFoundError as error:
                    raise CraftError("Unexpected error retrieving charm from instance.") from error

        emit.progress("Charm packed ok")
        return charm_name

    def handle_package(self, prime_dir, bases_config: BasesConfiguration):
        """Handle the final package creation."""
        emit.progress("Creating the package itself")
        zipname = format_charm_file_name(self.config.name, bases_config)
        zipfh = zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(prime_dir, followlinks=True):
            dirpath = pathlib.Path(dirpath)
            for filename in filenames:
                filepath = dirpath / filename
                zipfh.write(str(filepath), str(filepath.relative_to(prime_dir)))

        zipfh.close()
        return zipname
