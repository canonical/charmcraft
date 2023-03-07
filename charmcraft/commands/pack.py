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

"""Infrastructure for the 'pack' command."""

import pathlib
from typing import List

from craft_cli import emit, CraftError

from charmcraft import env, parts, instrum
from charmcraft.cmdbase import BaseCommand
from charmcraft.commands import build
from charmcraft.manifest import create_manifest
from charmcraft.parts import Step
from charmcraft.utils import load_yaml, build_zip

# the minimum set of files in a bundle
MANDATORY_FILES = ["bundle.yaml", "README.md"]

_overview = """
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


class PackCommand(BaseCommand):
    """Build the bundle or the charm.

    It uses the 'type' key in the configuration to decide which.
    """

    name = "pack"
    help_msg = "Build the charm or bundle"
    overview = _overview
    needs_config = True
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        self.include_format_option(parser)
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Launch shell in build environment upon failure",
        )
        parser.add_argument(
            "--destructive-mode",
            action="store_true",
            help=(
                "Pack charm using current host which may result in breaking "
                "changes to system configuration"
            ),
        )
        parser.add_argument(
            "--shell",
            action="store_true",
            help="Launch shell in build environment in lieu of packing",
        )
        parser.add_argument(
            "--shell-after",
            action="store_true",
            help="Launch shell in build environment after packing",
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

    def run(self, parsed_args):
        """Run the command."""
        # decide if this will work on a charm or a bundle
        if self.config.type == "charm":
            pack_method = self._pack_charm
        elif self.config.type == "bundle":
            pack_method = self._pack_bundle
        else:
            raise CraftError("Unknown type {!r} in charmcraft.yaml".format(self.config.type))

        with instrum.Timer("Whole pack run"):
            pack_method(parsed_args)

        if parsed_args.measure:
            instrum.dump(parsed_args.measure)

    def _validate_bases_indices(self, bases_indices):
        """Validate that bases index is valid."""
        if bases_indices is None:
            return

        msg = "Bases index '{}' is invalid (must be >= 0 and fit in configured bases)."
        len_configured_bases = len(self.config.bases)
        for bases_index in bases_indices:
            if bases_index < 0:
                raise CraftError(msg.format(bases_index))
            if bases_index >= len_configured_bases:
                raise CraftError(msg.format(bases_index))

    def _pack_charm(self, parsed_args) -> List[pathlib.Path]:
        """Pack a charm."""
        self._validate_bases_indices(parsed_args.bases_index)

        # build
        emit.progress("Packing the charm.")
        builder = build.Builder(
            config=self.config,
            force=parsed_args.force,
            debug=parsed_args.debug,
            shell=parsed_args.shell,
            shell_after=parsed_args.shell_after,
            measure=parsed_args.measure,
        )
        charms = builder.run(
            parsed_args.bases_index,
            destructive_mode=parsed_args.destructive_mode,
        )

        # avoid showing results when run inside a container (the outer charmcraft
        # is responsible of the final message to the user)
        if env.is_charmcraft_running_in_managed_mode():
            return

        if parsed_args.format:
            info = {"charms": charms}
            emit.message(self.format_content(parsed_args.format, info))
        else:
            emit.message("Charms packed:")
            for charm in charms:
                emit.message(f"    {charm}")

    def _pack_bundle(self, parsed_args) -> List[pathlib.Path]:
        """Pack a bundle."""
        emit.progress("Packing the bundle.")
        if parsed_args.shell:
            build.launch_shell()
            return []

        project = self.config.project

        if self.config.parts:
            config_parts = self.config.parts.copy()
        else:
            # "parts" not declared, create an implicit "bundle" part
            config_parts = {"bundle": {"plugin": "bundle"}}

        # a part named "bundle" using plugin "bundle" is special and has
        # predefined values set automatically.
        bundle_part = config_parts.get("bundle")
        if bundle_part and bundle_part.get("plugin") == "bundle":
            special_bundle_part = bundle_part
        else:
            special_bundle_part = None

        # get the config files
        bundle_filepath = project.dirpath / "bundle.yaml"
        bundle_config = load_yaml(bundle_filepath)
        if bundle_config is None:
            raise CraftError(
                "Missing or invalid main bundle file: {!r}.".format(str(bundle_filepath))
            )
        bundle_name = bundle_config.get("name")
        if not bundle_name:
            raise CraftError(
                "Invalid bundle config; missing a 'name' field indicating the bundle's name in "
                "file {!r}.".format(str(bundle_filepath))
            )

        if special_bundle_part:
            # set prime filters
            for fname in MANDATORY_FILES:
                fpath = project.dirpath / fname
                if not fpath.exists():
                    raise CraftError("Missing mandatory file: {!r}.".format(str(fpath)))
            prime = special_bundle_part.setdefault("prime", [])
            prime.extend(MANDATORY_FILES)

            # set source if empty or not declared in charm part
            if not special_bundle_part.get("source"):
                special_bundle_part["source"] = str(project.dirpath)

        if env.is_charmcraft_running_in_managed_mode():
            work_dir = env.get_managed_environment_home_path()
        else:
            work_dir = project.dirpath / build.BUILD_DIRNAME

        # run the parts lifecycle
        emit.debug(f"Parts definition: {config_parts}")
        lifecycle = parts.PartsLifecycle(
            config_parts,
            work_dir=work_dir,
            project_dir=project.dirpath,
            project_name=bundle_name,
            ignore_local_sources=[bundle_name + ".zip"],
        )
        try:
            lifecycle.run(Step.PRIME)
        except (RuntimeError, CraftError) as error:
            if parsed_args.debug:
                emit.debug(f"Error when running PRIME step: {error}")
                build.launch_shell()
            raise

        # pack everything
        create_manifest(lifecycle.prime_dir, project.started_at, None, [])
        zipname = project.dirpath / (bundle_name + ".zip")
        build_zip(zipname, lifecycle.prime_dir)

        if parsed_args.format:
            info = {"bundles": [str(zipname)]}
            emit.message(self.format_content(parsed_args.format, info))
        else:
            emit.message(f"Created {str(zipname)!r}.")

        if parsed_args.shell_after:
            build.launch_shell()

        return [zipname]
