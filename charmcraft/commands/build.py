# Copyright 2020-2022 Canonical Ltd.
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

"""Infrastructure for the 'build' command."""

import os
import pathlib
import subprocess
import zipfile
from typing import List, Optional, Tuple

from craft_cli import emit, EmitterMode, CraftError

from charmcraft import env, linters, parts
from charmcraft.bases import check_if_base_matches_host
from charmcraft.charm_builder import DISPATCH_FILENAME, HOOKS_DIR
from charmcraft.cmdbase import BaseCommand
from charmcraft.config import Base, BasesConfiguration, Config
from charmcraft.deprecations import notify_deprecation
from charmcraft.manifest import create_manifest
from charmcraft.metadata import parse_metadata_yaml
from charmcraft.parts import Step
from charmcraft.providers import capture_logs_from_instance, get_provider

# Some constants that are used through the code.
BUILD_DIRNAME = "build"
VENV_DIRNAME = "venv"

CHARM_FILES = [
    "metadata.yaml",
    DISPATCH_FILENAME,
    HOOKS_DIR,
]

CHARM_OPTIONAL = [
    "config.yaml",
    "metrics.yaml",
    "actions.yaml",
    "lxd-profile.yaml",
    "templates",
    "version",
    "lib",
    "mod",
    "LICENSE",
    "icon.svg",
    "README.md",
    "actions",
]


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

    def __init__(self, args, config):
        self.charmdir = args["from"]
        self.entrypoint = args["entrypoint"]
        self.requirement_paths = args["requirement"]
        self.force_packing = args["force"]
        self.debug = args["debug"]
        self.shell = args["shell"]
        self.shell_after = args["shell_after"]

        self.buildpath = self.charmdir / BUILD_DIRNAME
        self.config = config
        self.metadata = parse_metadata_yaml(self.charmdir)

        if self.config.parts:
            self._parts = self.config.parts.copy()
        else:
            # "parts" not declared, create an implicit "charm" part
            self._parts = {"charm": {"plugin": "charm"}}

        # a part named "charm" using plugin "charm" is special and has
        # predefined values set automatically.
        charm_part = self._parts.get("charm")
        if charm_part and charm_part.get("plugin") == "charm":
            self._special_charm_part = charm_part
        else:
            self._special_charm_part = None

        self.provider = get_provider()

    def show_linting_results(self, linting_results):
        """Manage the linters results, show some in different conditions, decide if continue."""
        attribute_results = []
        lint_results_by_outcome = {}
        for result in linting_results:
            if result.result == linters.IGNORED:
                continue
            if result.check_type == linters.CheckType.attribute:
                attribute_results.append(result)
            else:
                lint_results_by_outcome.setdefault(result.result, []).append(result)

        # show attribute results
        for result in attribute_results:
            emit.trace(
                f"Check result: {result.name} [{result.check_type}] {result.result} "
                f"({result.text}; see more at {result.url}).",
            )

        # show warnings (if any), then errors (if any)
        template = "- {0.name}: {0.text} ({0.url})"
        if linters.WARNINGS in lint_results_by_outcome:
            emit.message("Lint Warnings:", intermediate=True)
            for result in lint_results_by_outcome[linters.WARNINGS]:
                emit.message(template.format(result), intermediate=True)
        if linters.ERRORS in lint_results_by_outcome:
            emit.message("Lint Errors:", intermediate=True)
            for result in lint_results_by_outcome[linters.ERRORS]:
                emit.message(template.format(result), intermediate=True)
            if self.force_packing:
                emit.message("Packing anyway as requested.", intermediate=True)
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
        if env.is_charmcraft_running_in_managed_mode():
            work_dir = env.get_managed_environment_home_path()
        else:
            work_dir = self.buildpath

        emit.progress(f"Building charm in {str(work_dir)!r}")

        if self._special_charm_part:
            # all current deprecated arguments set charm plugin parameters
            self._handle_deprecated_cli_arguments()

            # add charm files to the prime filter
            self._set_prime_filter()

            # set source if empty or not declared in charm part
            if not self._special_charm_part.get("source"):
                self._special_charm_part["source"] = str(self.charmdir)

        # run the parts lifecycle
        emit.trace(f"Parts definition: {self._parts}")
        lifecycle = parts.PartsLifecycle(
            self._parts,
            work_dir=work_dir,
            project_dir=self.charmdir,
            project_name=self.metadata.name,
            ignore_local_sources=["*.charm"],
        )
        lifecycle.run(Step.PRIME)

        # run linters and show the results
        linting_results = linters.analyze(self.config, lifecycle.prime_dir)
        self.show_linting_results(linting_results)

        create_manifest(
            lifecycle.prime_dir,
            self.config.project.started_at,
            bases_config,
            linting_results,
        )

        zipname = self.handle_package(lifecycle.prime_dir, bases_config)
        emit.message(f"Created '{zipname}'.", intermediate=True)
        return zipname

    def _handle_deprecated_cli_arguments(self):
        # verify if deprecated --requirement is used and update the plugin property
        if self._special_charm_part.get("charm-requirements"):
            if self.requirement_paths:
                raise CraftError(
                    "--requirement not supported when charm-requirements "
                    "specified in charmcraft.yaml"
                )
        else:
            if self.requirement_paths:
                self._special_charm_part["charm-requirements"] = [
                    str(p) for p in self.requirement_paths
                ]
                self.requirement_paths = None
            else:
                default_reqfile = self.charmdir / "requirements.txt"
                if default_reqfile.is_file():
                    self._special_charm_part["charm-requirements"] = ["requirements.txt"]
                else:
                    self._special_charm_part["charm-requirements"] = []

        # verify if deprecated --entrypoint is used and update the plugin property
        if self._special_charm_part.get("charm-entrypoint"):
            if self.entrypoint:
                raise CraftError(
                    "--entrypoint not supported when charm-entrypoint "
                    "specified in charmcraft.yaml"
                )
            entrypoint = self._special_charm_part.get("charm-entrypoint")
        elif self.entrypoint:
            entrypoint = self.entrypoint
            self.entrypoint = None
        else:
            entrypoint = "src/charm.py"

        # store the entrypoint always relative to the project's path (no matter if the origin
        # was relative or absolute)
        rel_entrypoint = (self.charmdir / entrypoint).relative_to(self.charmdir)
        self._special_charm_part["charm-entrypoint"] = rel_entrypoint.as_posix()

        # validate the entrypoint (no matter if it came from the config or it's the default)
        filepath = (self.charmdir / self._special_charm_part["charm-entrypoint"]).resolve()
        if not filepath.exists():
            raise CraftError("Charm entry point was not found: {!r}".format(str(filepath)))
        if self.charmdir not in filepath.parents:
            raise CraftError(
                "Charm entry point must be inside the project: {!r}".format(str(filepath))
            )
        if not os.access(filepath, os.X_OK):
            raise CraftError("Charm entry point must be executable: {!r}".format(str(filepath)))

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
        if (
            self._special_charm_part.get("charm-requirements")
            or self._special_charm_part.get("charm-binary-python-packages")
            or self._special_charm_part.get("charm-python-packages")
        ):
            charm_part_prime.append(VENV_DIRNAME)

        # add mandatory and optional charm files
        charm_part_prime.extend(CHARM_FILES)
        for fn in CHARM_OPTIONAL:
            path = self.charmdir / fn
            if path.exists():
                charm_part_prime.append(fn)

    def plan(
        self, *, bases_indices: Optional[List[int]], destructive_mode: bool, managed_mode: bool
    ) -> List[Tuple[BasesConfiguration, Base, int, int]]:
        """Determine the build plan based on user inputs and host environment.

        Provide a list of bases that are buildable and scoped according to user
        configuration. Provide all relevant details including the applicable
        bases configuration and the indices of the entries to build for.

        :returns: List of Tuples (bases_config, build_on, bases_index, build_on_index).
        """
        build_plan: List[Tuple[BasesConfiguration, Base, int, int]] = []

        for bases_index, bases_config in enumerate(self.config.bases):
            if bases_indices and bases_index not in bases_indices:
                emit.trace(f"Skipping 'bases[{bases_index:d}]' due to --base-index usage.")
                continue

            for build_on_index, build_on in enumerate(bases_config.build_on):
                if managed_mode or destructive_mode:
                    matches, reason = check_if_base_matches_host(build_on)
                else:
                    matches, reason = self.provider.is_base_available(build_on)

                if matches:
                    emit.trace(
                        f"Building for 'bases[{bases_index:d}]' "
                        f"as host matches 'build-on[{build_on_index:d}]'.",
                    )
                    build_plan.append((bases_config, build_on, bases_index, build_on_index))
                    break
                else:
                    emit.progress(
                        f"Skipping 'bases[{bases_index:d}].build-on[{build_on_index:d}]': "
                        f"{reason}.",
                    )
            else:
                emit.message(
                    "No suitable 'build-on' environment found "
                    f"in 'bases[{bases_index:d}]' configuration.",
                    intermediate=True,
                )

        return build_plan

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

        managed_mode = env.is_charmcraft_running_in_managed_mode()
        if not managed_mode and not destructive_mode:
            self.provider.ensure_provider_is_available()

        if self.entrypoint:
            notify_deprecation("dn04")

        if self.requirement_paths:
            notify_deprecation("dn05")

        build_plan = self.plan(
            bases_indices=bases_indices,
            destructive_mode=destructive_mode,
            managed_mode=managed_mode,
        )
        if not build_plan:
            raise CraftError(
                "No suitable 'build-on' environment found in any 'bases' configuration."
            )

        charms = []
        for bases_config, build_on, bases_index, build_on_index in build_plan:
            emit.trace(f"Building for 'bases[{ bases_index:d}][{build_on_index:d}]'.")
            if managed_mode or destructive_mode:
                if self.shell:
                    # Execute shell in lieu of build.
                    launch_shell()
                    continue

                try:
                    charm_name = self.build_charm(bases_config)
                except (CraftError, RuntimeError) as error:
                    if self.debug:
                        emit.trace(f"Launching shell as charm building ended in error: {error}")
                        launch_shell()
                    raise

                if self.shell_after:
                    launch_shell()
            else:
                charm_name = self.pack_charm_in_instance(
                    bases_index=bases_index,
                    build_on=build_on,
                    build_on_index=build_on_index,
                )
            charms.append(charm_name)

        return charms

    def pack_charm_in_instance(
        self, *, bases_index: int, build_on: Base, build_on_index: int
    ) -> str:
        """Pack instance in Charm."""
        charm_name = format_charm_file_name(self.metadata.name, self.config.bases[bases_index])

        # If building in project directory, use the project path as the working
        # directory. The output charms will be placed in the correct directory
        # without needing retrieval. If outputting to a directory other than the
        # charm project directory, we need to output the charm outside the
        # project directory and can retrieve it when complete.
        cwd = pathlib.Path.cwd()
        if cwd == self.charmdir:
            instance_output_dir = env.get_managed_environment_project_path()
            pull_charm = False
        else:
            instance_output_dir = env.get_managed_environment_home_path()
            pull_charm = True

        cmd = ["charmcraft", "pack", "--bases-index", str(bases_index)]

        if emit.get_mode() == EmitterMode.VERBOSE:
            cmd.append("--verbose")
        elif emit.get_mode() == EmitterMode.QUIET:
            cmd.append("--quiet")
        elif emit.get_mode() == EmitterMode.TRACE:
            cmd.append("--trace")

        if self.debug:
            cmd.append("--debug")

        if self.shell:
            cmd.append("--shell")

        if self.shell_after:
            cmd.append("--shell-after")

        emit.progress(
            f"Launching environment to pack for base {build_on} "
            "(may take a while the first time but it's reusable)"
        )
        with self.provider.launched_environment(
            charm_name=self.metadata.name,
            project_path=self.charmdir,
            base=build_on,
            bases_index=bases_index,
            build_on_index=build_on_index,
        ) as instance:
            emit.progress("Packing the charm")
            emit.trace(f"Running {cmd}")
            try:
                with emit.pause():
                    instance.execute_run(cmd, check=True, cwd=instance_output_dir)
            except subprocess.CalledProcessError as error:
                raise CraftError(
                    f"Failed to build charm for bases index '{bases_index}'."
                ) from error
            finally:
                capture_logs_from_instance(instance)

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
        zipname = format_charm_file_name(self.metadata.name, bases_config)
        zipfh = zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(prime_dir, followlinks=True):
            dirpath = pathlib.Path(dirpath)
            for filename in filenames:
                filepath = dirpath / filename
                zipfh.write(str(filepath), str(filepath.relative_to(prime_dir)))

        zipfh.close()
        return zipname


class Validator:
    """A validator of all received options."""

    _options = [
        "from",  # this needs to be processed first, as it's a base dir to find other files
        "destructive_mode",
        "entrypoint",
        "requirement",
        "bases_indices",
        "force",
        "debug",
        "shell",
        "shell_after",
    ]

    def __init__(self, config: Config):
        self.basedir = None  # this will be fulfilled when processing 'from'
        self.config = config

    def process(self, parsed_args):
        """Process the received options."""
        result = {}
        for opt in self._options:
            meth = getattr(self, "validate_" + opt)
            result[opt] = meth(getattr(parsed_args, opt, None))
        return result

    def validate_bases_indices(self, bases_indices):
        """Validate that bases index is valid."""
        if not bases_indices:
            return

        for bases_index in bases_indices:
            if bases_index < 0:
                raise CraftError(f"Bases index '{bases_index}' is invalid (must be >= 0).")

            if not self.config.bases:
                raise CraftError(
                    "No bases configuration found, required when using --bases-index.",
                )

            if bases_index >= len(self.config.bases):
                raise CraftError(
                    f"No bases configuration found for specified index '{bases_index}'."
                )

    def validate_debug(self, value):
        """Validate the value (just convert to bool to make None explicit)."""
        return bool(value)

    def validate_destructive_mode(self, destructive_mode):
        """Validate that destructive mode option is valid."""
        if not isinstance(destructive_mode, bool):
            return False

        return destructive_mode

    def validate_from(self, dirpath):
        """Validate that the charm dir is there and yes, a directory."""
        if dirpath is None:
            dirpath = pathlib.Path.cwd()
        else:
            dirpath = dirpath.expanduser().absolute()

        if not dirpath.exists():
            raise CraftError("Charm directory was not found: {!r}".format(str(dirpath)))
        if not dirpath.is_dir():
            raise CraftError(
                "Charm directory is not really a directory: {!r}".format(str(dirpath))
            )

        self.basedir = dirpath
        return dirpath

    def validate_entrypoint(self, filepath):
        """Validate that the entrypoint exists and is executable."""
        if filepath is None:
            return None

        filepath = filepath.expanduser().absolute()

        if not filepath.exists():
            raise CraftError("Charm entry point was not found: {!r}".format(str(filepath)))
        if self.basedir not in filepath.parents:
            raise CraftError(
                "Charm entry point must be inside the project: {!r}".format(str(filepath))
            )
        if not os.access(filepath, os.X_OK):
            raise CraftError("Charm entry point must be executable: {!r}".format(str(filepath)))
        return filepath

    def validate_requirement(self, filepaths):
        """Validate that the given requirement(s) (if any) exist."""
        if filepaths is None:
            return []

        filepaths = [x.expanduser().absolute() for x in filepaths]
        for fpath in filepaths:
            if not fpath.exists():
                raise CraftError("the requirements file was not found: {!r}".format(str(fpath)))
        return filepaths

    def validate_shell(self, value):
        """Validate the value (just convert to bool to make None explicit)."""
        return bool(value)

    def validate_shell_after(self, value):
        """Validate the value (just convert to bool to make None explicit)."""
        return bool(value)

    def validate_force(self, value):
        """Validate the value (just convert to bool to make None explicit)."""
        return bool(value)


_overview = """
Build a charm operator package.

You can `juju deploy` the resulting `.charm` file directly, or upload it
to Charmhub with `charmcraft upload`.

You must be inside a charm directory with a valid `metadata.yaml`,
`requirements.txt` including the `ops` package for the Python operator
framework, and an operator entrypoint, usually `src/charm.py`.

See `charmcraft init` to create a template charm directory structure.
"""


class BuildCommand(BaseCommand):
    """Build the charm."""

    name = "build"
    help_msg = "Build the charm"
    overview = _overview
    hidden = True
    needs_config = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            "-f",
            "--from",
            type=pathlib.Path,
            help="Charm directory with metadata.yaml where the build "
            "takes place; defaults to '.'",
        )
        parser.add_argument(
            "-e",
            "--entrypoint",
            type=pathlib.Path,
            help="The executable which is the operator entry point; " "defaults to 'src/charm.py'",
        )
        parser.add_argument(
            "-r",
            "--requirement",
            action="append",
            type=pathlib.Path,
            help="File(s) listing needed PyPI dependencies (can be used multiple "
            "times); defaults to 'requirements.txt'",
        )

    def run(self, parsed_args):
        """Run the command."""
        # this command is deprecated now (note that the whole infrastructure behind
        # is ok to use, but through PackCommand)
        notify_deprecation("dn06")

        validator = Validator(self.config)
        args = validator.process(parsed_args)
        emit.trace(f"Working arguments: {args}")
        builder = Builder(args, self.config)
        builder.run(destructive_mode=args["destructive_mode"])
