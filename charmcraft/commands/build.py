# Copyright 2020-2021 Canonical Ltd.
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

import logging
import os
import pathlib
import subprocess
import zipfile
from typing import List, Optional

from charmcraft import linters, parts
from charmcraft.bases import check_if_base_matches_host
from charmcraft.cmdbase import BaseCommand, CommandError
from charmcraft.config import Base, BasesConfiguration, Config
from charmcraft.deprecations import notify_deprecation
from charmcraft.env import (
    get_managed_environment_home_path,
    get_managed_environment_project_path,
    is_charmcraft_running_in_managed_mode,
)
from charmcraft.logsetup import message_handler
from charmcraft.manifest import create_manifest
from charmcraft.metadata import parse_metadata_yaml
from charmcraft.parts import Step
from charmcraft.providers import (
    capture_logs_from_instance,
    ensure_provider_is_available,
    is_base_providable,
    launched_environment,
)

logger = logging.getLogger(__name__)

# Some constants that are used through the code.
BUILD_DIRNAME = "build"
VENV_DIRNAME = "venv"

# The file name and template for the dispatch script
DISPATCH_FILENAME = "dispatch"
# If Juju doesn't support the dispatch mechanism, it will execute the
# hook, and we'd need sys.argv[0] to be the name of the hook but it's
# geting lost by calling this dispatch, so we fake JUJU_DISPATCH_PATH
# to be the value it would've otherwise been.
DISPATCH_CONTENT = """#!/bin/sh

JUJU_DISPATCH_PATH="${{JUJU_DISPATCH_PATH:-$0}}" PYTHONPATH=lib:venv ./{entrypoint_relative_path}
"""

# The minimum set of hooks to be provided for compatibility with old Juju
MANDATORY_HOOK_NAMES = {"install", "start", "upgrade-charm"}
HOOKS_DIR = "hooks"

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
]


def _format_run_on_base(base: Base) -> str:
    """Formulate charm string for base section."""
    return "-".join([base.name, base.channel, *base.architectures])


def _format_bases_config(bases_config: BasesConfiguration) -> str:
    """Formulate charm string for bases configuration section."""
    return "_".join([_format_run_on_base(r) for r in bases_config.run_on])


def format_charm_file_name(
    charm_name: str, bases_config: Optional[BasesConfiguration] = None
) -> str:
    """Formulate charm file name.

    :param charm_name: Name of charm.
    :param bases_config: Bases configuration for charm.  None will use legacy
        format that will be removed shortly.

    :returns: File name string, including .charm extension.
    """
    # TODO: Patterson 2021-06-14 Temporary legacy support prior to bases configuration.
    if bases_config is None:
        return charm_name + ".charm"

    return "_".join([charm_name, _format_bases_config(bases_config)]) + ".charm"


def polite_exec(cmd):
    """Execute a command, only showing output if error."""
    logger.debug("Running external command %s", cmd)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
    except Exception as err:
        logger.error("Executing %s crashed with %r", cmd, err)
        return 1

    for line in proc.stdout:
        logger.debug(":: %s", line.rstrip())
    retcode = proc.wait()

    if retcode:
        logger.error("Executing %s failed with return code %d", cmd, retcode)
    return retcode


def relativise(src, dst):
    """Build a relative path from src to dst."""
    return pathlib.Path(os.path.relpath(str(dst), str(src.parent)))


class Builder:
    """The package builder."""

    def __init__(self, args, config):
        self.charmdir = args["from"]
        self.entrypoint = args["entrypoint"]
        self.requirement_paths = args["requirement"]
        self.force_packing = args["force"]

        self.buildpath = self.charmdir / BUILD_DIRNAME
        self.config = config
        self.metadata = parse_metadata_yaml(self.charmdir)

        self._parts = self.config.parts.copy()
        self._charm_part = self._parts.setdefault("charm", {})
        self._prime = self._charm_part.setdefault("prime", [])

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
            logger.debug(
                "Check result: %s [%s] %s (%s; see more at %s).",
                result.name,
                result.check_type,
                result.result,
                result.text,
                result.url,
            )

        # show warnings (if any), then errors (if any)
        template = "- %s: %s (%s)"
        if linters.WARNINGS in lint_results_by_outcome:
            logger.info("Lint Warnings:")
            for result in lint_results_by_outcome[linters.WARNINGS]:
                logger.info(template, result.name, result.text, result.url)
        if linters.ERRORS in lint_results_by_outcome:
            logger.info("Lint Errors:")
            for result in lint_results_by_outcome[linters.ERRORS]:
                logger.info(template, result.name, result.text, result.url)
            if self.force_packing:
                logger.info("Packing anyway as requested.")
            else:
                raise CommandError(
                    "Aborting due to lint errors (use --force to override).", retcode=2
                )

    def build_charm(self, bases_config: BasesConfiguration) -> str:
        """Build the charm.

        :param bases_config: Bases configuration to use for build.

        :returns: File name of charm.
        """
        logger.debug("Building charm in %r", str(self.buildpath))

        self._handle_deprecated_cli_arguments()

        # add charm files to the prime filter
        self._set_prime_filter()

        # set source for buiding
        self._charm_part["source"] = str(self.charmdir)

        # run the parts lifecycle
        logger.debug("Parts definition: %s", self._parts)
        lifecycle = parts.PartsLifecycle(
            self._parts,
            work_dir=self.buildpath,
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
        logger.info("Created '%s'.", zipname)
        return zipname

    def _handle_deprecated_cli_arguments(self):
        # verify if deprecated --requirement is used and update the plugin property
        if self._charm_part.get("charm-requirements"):
            if self.requirement_paths:
                raise CommandError(
                    "--requirement not supported when charm-requirements "
                    "specified in charmcraft.yaml"
                )
        else:
            if self.requirement_paths:
                self._charm_part["charm-requirements"] = [str(p) for p in self.requirement_paths]
                self.requirement_paths = None
            else:
                default_reqfile = self.charmdir / "requirements.txt"
                if default_reqfile.is_file():
                    self._charm_part["charm-requirements"] = ["requirements.txt"]
                else:
                    self._charm_part["charm-requirements"] = []

        # verify if deprecated --entrypoint is used and update the plugin property
        if self._charm_part.get("charm-entrypoint"):
            if self.entrypoint:
                raise CommandError(
                    "--entrypoint not supported when charm-entrypoint "
                    "specified in charmcraft.yaml"
                )
        else:
            if self.entrypoint:
                rel_entrypoint = self.entrypoint.relative_to(self.charmdir)
                self._charm_part["charm-entrypoint"] = str(rel_entrypoint)
                self.entrypoint = None
            else:
                self._charm_part["charm-entrypoint"] = "src/charm.py"

    def _set_prime_filter(self):
        """Add mandatory and optional charm files to the prime filter.

        The prime filter should contain:
        - The charm entry point, or the directory containing it if it's
          not directly in the project dir.
        - A set of mandatory charm files, including metadata.yaml, the
          dispatcher and the hooks directory.
        - A set of optional charm files.
        """
        # add entrypoint
        entrypoint = pathlib.Path(self._charm_part["charm-entrypoint"])
        if str(entrypoint) == entrypoint.name:
            # the entry point is in the root of the project, just include it
            self._prime.append(str(entrypoint))
        else:
            # the entry point is in a subdir, include the whole subtree
            self._prime.append(str(entrypoint.parts[0]))

        # add venv if there are requirements
        if self._charm_part["charm-requirements"]:
            self._prime.append(VENV_DIRNAME)

        # add mandatory and optional charm files
        self._prime.extend(CHARM_FILES)
        for fn in CHARM_OPTIONAL:
            path = self.charmdir / fn
            if path.exists():
                self._prime.append(fn)

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

        managed_mode = is_charmcraft_running_in_managed_mode()
        if not managed_mode and not destructive_mode:
            ensure_provider_is_available()

        if self.entrypoint:
            notify_deprecation("dn04")

        if self.requirement_paths:
            notify_deprecation("dn05")

        if not (self.charmdir / "charmcraft.yaml").exists():
            notify_deprecation("dn02")

        for bases_index, bases_config in enumerate(self.config.bases):
            if bases_indices and bases_index not in bases_indices:
                logger.debug(
                    "Skipping 'bases[%d]' due to --base-index usage.",
                    bases_index,
                )
                continue

            for build_on_index, build_on in enumerate(bases_config.build_on):
                if managed_mode or destructive_mode:
                    matches, reason = check_if_base_matches_host(build_on)
                else:
                    matches, reason = is_base_providable(build_on)

                if matches:
                    logger.debug(
                        "Building for 'bases[%d]' as host matches 'build-on[%d]'.",
                        bases_index,
                        build_on_index,
                    )
                    if managed_mode or destructive_mode:
                        charm_name = self.build_charm(bases_config)
                    else:
                        charm_name = self.pack_charm_in_instance(
                            bases_index=bases_index,
                            build_on=build_on,
                            build_on_index=build_on_index,
                        )

                    charms.append(charm_name)
                    break
                else:
                    logger.info(
                        "Skipping 'bases[%d].build-on[%d]': %s.",
                        bases_index,
                        build_on_index,
                        reason,
                    )
            else:
                logger.warning(
                    "No suitable 'build-on' environment found in 'bases[%d]' configuration.",
                    bases_index,
                )

        if not charms:
            raise CommandError(
                "No suitable 'build-on' environment found in any 'bases' configuration."
            )

        return charms

    def pack_charm_in_instance(
        self, *, bases_index: int, build_on: Base, build_on_index: int
    ) -> str:
        """Pack instance in Charm."""
        charm_name = format_charm_file_name(self.metadata.name, self.config.bases[bases_index])

        # If building in project directory, use the project path as the working
        # directory. The output charms will be placed in the correct directory
        # without needing retrieval. If outputing to a directory other than the
        # charm project directory, we need to output the charm outside the
        # project directory and can retrieve it when complete.
        cwd = pathlib.Path.cwd()
        if cwd == self.charmdir:
            instance_output_dir = get_managed_environment_project_path()
            pull_charm = False
        else:
            instance_output_dir = get_managed_environment_home_path()
            pull_charm = True

        cmd = ["charmcraft", "pack", "--bases-index", str(bases_index)]

        if message_handler.mode == message_handler.VERBOSE:
            cmd.append("--verbose")
        elif message_handler.mode == message_handler.QUIET:
            cmd.append("--quiet")

        logger.info(f"Packing charm {charm_name!r}...")
        with launched_environment(
            charm_name=self.metadata.name,
            project_path=self.charmdir,
            base=build_on,
            bases_index=bases_index,
            build_on_index=build_on_index,
        ) as instance:
            try:
                instance.execute_run(
                    cmd,
                    check=True,
                    cwd=instance_output_dir.as_posix(),
                )
            except subprocess.CalledProcessError as error:
                capture_logs_from_instance(instance)
                raise CommandError(
                    f"Failed to build charm for bases index '{bases_index}'."
                ) from error

            if pull_charm:
                try:
                    instance.pull_file(
                        source=instance_output_dir / charm_name,
                        destination=cwd / charm_name,
                    )
                except FileNotFoundError as error:
                    raise CommandError(
                        "Unexpected error retrieving charm from instance."
                    ) from error

        return charm_name

    def handle_package(self, prime_dir, bases_config: Optional[BasesConfiguration] = None):
        """Handle the final package creation."""
        logger.debug("Creating the package itself")
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
                raise CommandError(f"Bases index '{bases_index}' is invalid (must be >= 0).")

            if not self.config.bases:
                raise CommandError(
                    "No bases configuration found, required when using --bases-index.",
                )

            if bases_index >= len(self.config.bases):
                raise CommandError(
                    f"No bases configuration found for specified index '{bases_index}'."
                )

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
            raise CommandError("Charm directory was not found: {!r}".format(str(dirpath)))
        if not dirpath.is_dir():
            raise CommandError(
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
            raise CommandError("Charm entry point was not found: {!r}".format(str(filepath)))
        if self.basedir not in filepath.parents:
            raise CommandError(
                "Charm entry point must be inside the project: {!r}".format(str(filepath))
            )
        if not os.access(filepath, os.X_OK):
            raise CommandError("Charm entry point must be executable: {!r}".format(str(filepath)))
        return filepath

    def validate_requirement(self, filepaths):
        """Validate that the given requirement(s) (if any) exist.

        If not specified, default to requirements.txt if there.
        """
        if filepaths is None:
            return []

        filepaths = [x.expanduser().absolute() for x in filepaths]
        for fpath in filepaths:
            if not fpath.exists():
                raise CommandError("the requirements file was not found: {!r}".format(str(fpath)))
        return filepaths

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
    common = True

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
        validator = Validator(self.config)
        args = validator.process(parsed_args)
        logger.debug("working arguments: %s", args)
        builder = Builder(args, self.config)
        builder.run(destructive_mode=args["destructive_mode"])
