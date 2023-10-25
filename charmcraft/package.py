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
import dataclasses
import os
import pathlib
import shutil
import subprocess
import tempfile
import zipfile
from typing import Collection, Dict, List, Mapping, Optional, Sequence

import craft_parts
import yaml
from craft_cli import CraftError, emit
from craft_providers.bases import get_base_alias

import charmcraft.env
import charmcraft.instrum
import charmcraft.linters
import charmcraft.providers
from charmcraft import const, env, errors, parts
from charmcraft.metafiles.actions import create_actions_yaml
from charmcraft.metafiles.config import create_config_yaml
from charmcraft.metafiles.manifest import create_manifest
from charmcraft.metafiles.metadata import create_metadata_yaml
from charmcraft.models.charmcraft import Base, BasesConfiguration
from charmcraft.models.lint import LintResult
from charmcraft.utils import (
    build_zip,
    collect_charmlib_pydeps,
    get_host_architecture,
    humanize_list,
    load_yaml,
)


@dataclasses.dataclass(frozen=True)
class OutputFiles:
    """Collection of output files, separated into charms and an optional bundle."""

    charms: Sequence[pathlib.Path] = ()
    bundles: Sequence[pathlib.Path] = ()


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

    def __init__(
        self,
        *,
        config,
        force,
        debug,
        shell,
        shell_after,
        measure,
    ):
        self.force_packing = force
        self.debug = debug
        self.shell = shell
        self.shell_after = shell_after
        self.measure = measure

        self.charmdir = config.project.dirpath
        self.buildpath = self.charmdir / const.BUILD_DIRNAME
        self.shared_cache_path = charmcraft.env.get_host_shared_cache_path()

        self.config = config
        if self.config.parts:
            self._parts = self.config.parts.copy()
        else:
            self._parts = None

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
            if result.result == LintResult.IGNORED:
                continue
            if result.check_type == charmcraft.linters.CheckType.ATTRIBUTE:
                attribute_results.append(result)
            else:
                lint_results_by_outcome.setdefault(result.result, []).append(result)

        # show attribute results
        for result in attribute_results:
            emit.verbose(
                f"Check result: {result.name} [{result.check_type.value}] {result.result} "
                f"({result.text}; see more at {result.url}).",
            )

        # show warnings (if any), then errors (if any)
        template = "- {0.name}: {0.text} ({0.url})"
        if LintResult.WARNINGS in lint_results_by_outcome:
            emit.progress("Lint Warnings:", permanent=True)
            for result in lint_results_by_outcome[LintResult.WARNINGS]:
                emit.progress(template.format(result), permanent=True)
        if LintResult.ERRORS in lint_results_by_outcome:
            emit.progress("Lint Errors:", permanent=True)
            for result in lint_results_by_outcome[LintResult.ERRORS]:
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
            lifecycle.run(craft_parts.Step.PRIME)

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
            charm_part_prime.append(const.VENV_DIRNAME)

        # add mandatory and optional charm files
        charm_part_prime.extend(const.CHARM_MANDATORY_FILES)
        for fn in const.CHARM_OPTIONAL_FILES:
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
            shared_cache_path=self.shared_cache_path,
        )

        if build_on.name == "ubuntu":
            if build_on.channel in const.UBUNTU_LTS_STABLE:
                allow_unstable = False
            else:
                allow_unstable = True
                emit.progress(
                    f"Warning: non-LTS Ubuntu releases {build_on.channel} are "
                    "intended for experimental use only.",
                    permanent=True,
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
        for dirpath, _dirnames, filenames in os.walk(prime_dir, followlinks=True):
            dirpath = pathlib.Path(dirpath)
            for filename in filenames:
                filepath = dirpath / filename
                zipfh.write(str(filepath), str(filepath.relative_to(prime_dir)))

        zipfh.close()
        return zipname

    def _get_charm_pack_args(self, base_indeces: List[str], destructive_mode: bool) -> List[str]:
        """Get the arguments for a charmcraft pack subprocess to run."""
        args = ["charmcraft", "pack", "--verbose"]
        if destructive_mode:
            args.append("--destructive-mode")
        for base in base_indeces:
            args.append(f"--bases-index={base}")
        if self.force_packing:
            args.append("--force")
        return args

    def pack_bundle(
        self,
        *,
        charms: Dict[str, pathlib.Path],
        base_indeces: List[str],
        destructive_mode: bool,
        overwrite: bool = False,
    ) -> OutputFiles:
        """Pack a bundle."""
        if self._parts is None:
            self._parts = {"bundle": {"plugin": "bundle"}}

        if env.is_charmcraft_running_in_managed_mode():
            work_dir = env.get_managed_environment_home_path()
        else:
            work_dir = self.config.project.dirpath / const.BUILD_DIRNAME

        # get the config files
        bundle_filepath = self.config.project.dirpath / const.BUNDLE_FILENAME
        bundle = load_yaml(bundle_filepath)
        bundle_name = bundle.get("name")
        if not bundle_name:
            raise CraftError(
                "Invalid bundle config; missing a 'name' field indicating the bundle's name in "
                f"file {str(bundle_filepath)!r}."
            )

        if charms:
            bundle_charms = bundle.get("applications", {})
            command_args = self._get_charm_pack_args(base_indeces, destructive_mode)
            charms = _subprocess_pack_charms(charms, command_args)
            for name, value in bundle_charms.items():
                if name in charms:
                    value["charm"] = charms[name]
        else:
            charms = {}

        lifecycle = parts.PartsLifecycle(
            self._parts,
            work_dir=work_dir,
            project_dir=self.config.project.dirpath,
            project_name=bundle_name,
            ignore_local_sources=[bundle_name + ".zip"],
        )

        lifecycle.run(craft_parts.Step.PRIME)

        # pack everything
        create_manifest(
            lifecycle.prime_dir,
            self.config.project.started_at,
            bases_config=None,
            linting_results=[],
        )
        zipname = self.config.project.dirpath / (bundle_name + ".zip")
        if overwrite:
            primed_bundle_path = lifecycle.prime_dir / const.BUNDLE_FILENAME
            with primed_bundle_path.open("w") as bundle_file:
                yaml.safe_dump(bundle, bundle_file)
        build_zip(zipname, lifecycle.prime_dir)

        return OutputFiles(charms=list(charms.values()), bundles=[zipname])


def _subprocess_pack_charms(
    charms: Mapping[str, pathlib.Path],
    command_args: Collection[str],
) -> Dict[str, pathlib.Path]:
    """Pack the given charms for a bundle in subprocesses.

    :param command_args: The initial arguments
    :param charms: A mapping of charm name to charm path
    :returns: A mapping of charm names to the generated charm.
    """
    if charms:
        charm_str = humanize_list(charms.keys(), "and")
        emit.progress(f"Packing charms: {charm_str}...")
    cwd = pathlib.Path(os.getcwd()).resolve()
    generated_charms = {}
    with tempfile.TemporaryDirectory(prefix="charmcraft-bundle-", dir=cwd) as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        try:
            # Put all the charms in this temporary directory.
            os.chdir(temp_dir)
            for charm, project_dir in charms.items():
                full_command = [*command_args, f"--project-dir={project_dir}"]
                with emit.open_stream(f"Packing charm {charm}...") as stream:
                    subprocess.check_call(full_command, stdout=stream, stderr=stream)
            duplicate_charms = {}
            for charm_file in temp_dir.glob("*.charm"):
                charm_name = charm_file.name.partition("_")[0]
                if charm_name not in charms:
                    emit.debug(f"Unknown charm file generated: {charm_file.name}")
                    continue
                if charm_name in generated_charms:
                    if charm_name not in duplicate_charms:
                        duplicate_charms[charm_name] = temp_dir.glob(f"{charm_name}_*.charm")
                    continue
                generated_charms[charm_name] = charm_file
            if duplicate_charms:
                raise errors.DuplicateCharmsError(duplicate_charms)
            for charm, charm_file in generated_charms.items():
                destination = cwd / charm_file.name
                destination.unlink(missing_ok=True)
                generated_charms[charm] = shutil.move(charm_file, destination)
        finally:
            os.chdir(cwd)
    return generated_charms
