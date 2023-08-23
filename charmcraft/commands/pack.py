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
import argparse
import pathlib
from typing import Dict, List

import yaml
from craft_cli import ArgumentParsingError, CraftError, emit

from charmcraft import env, instrum, package
from charmcraft.cmdbase import BaseCommand
from charmcraft.utils import find_charm_sources, get_charm_name_from_path, load_yaml

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

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Run the command."""
        self._check_config(config_file=True)

        builder = package.Builder(
            config=self.config,
            force=parsed_args.force,
            debug=parsed_args.debug,
            shell=parsed_args.shell,
            shell_after=parsed_args.shell_after,
            measure=parsed_args.measure,
        )

        # decide if this will work on a charm or a bundle
        if self.config.type == "charm":
            if parsed_args.include_all_charms:
                raise ArgumentParsingError(
                    "--include-all-charms can only be used when packing a bundle. "
                    f"Currently trying to pack: {self.config.project.dirpath}"
                )
            if parsed_args.include_charm:
                raise ArgumentParsingError(
                    "--include-charm can only be used when packing a bundle. "
                    f"Currently trying to pack: {self.config.project.dirpath}"
                )
            if parsed_args.output_bundle:
                raise ArgumentParsingError(
                    "--output-bundle can only be used when packing a bundle. "
                    f"Currently trying to pack: {self.config.project.dirpath}"
                )
            self._check_config(bases=True)
            with instrum.Timer("Whole pack run"):
                self._pack_charm(parsed_args, builder)
        elif self.config.type == "bundle":
            if parsed_args.shell:
                package.launch_shell()
                return
            bundle_filepath = self.config.project.dirpath / "bundle.yaml"
            bundle = load_yaml(bundle_filepath)
            if bundle is None:
                raise CraftError(f"Missing or invalid main bundle file: {str(bundle_filepath)!r}.")
            if parsed_args.include_all_charms:
                charm_names = bundle.get("applications", {}).keys()
                charms = find_charm_sources(self.config.project.dirpath, charm_names)
            elif parsed_args.include_charm:
                charms: Dict[str, pathlib.Path] = {}
                for path in parsed_args.include_charm:
                    if not path.is_absolute():
                        path = self.config.project.dirpath / path
                    name = get_charm_name_from_path(path)
                    charms[name] = path
            else:
                charms = {}
            with instrum.Timer("Whole pack run"):
                self._pack_bundle(parsed_args, charms, builder)
            if parsed_args.output_bundle:
                with parsed_args.output_bundle.open("wt") as file:
                    yaml.safe_dump(bundle, file)
        else:
            raise CraftError(f"Unknown type {self.config.type!r} in charmcraft.yaml")

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

    def _pack_charm(self, parsed_args, builder: package.Builder) -> List[pathlib.Path]:
        """Pack a charm."""
        self._validate_bases_indices(parsed_args.bases_index)

        # build
        emit.progress("Packing the charm.")
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

    def _pack_bundle(
        self,
        parsed_args: argparse.Namespace,
        charms: Dict[str, pathlib.Path],
        builder: package.Builder,
        overwrite_bundle: bool = False,
    ) -> None:
        """Pack a bundle."""
        emit.progress("Packing the bundle.")
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
            # set prime filters
            for fname in MANDATORY_FILES:
                fpath = project.dirpath / fname
                if not fpath.exists():
                    raise CraftError(f"Missing mandatory file: {str(fpath)!r}.")
            prime = bundle_part.setdefault("prime", [])
            prime.extend(MANDATORY_FILES)

            # set source if empty or not declared in charm part
            if not bundle_part.get("source"):
                bundle_part["source"] = str(project.dirpath)

        # run the parts lifecycle
        emit.debug(f"Parts definition: {config_parts}")

        try:
            output_files = builder.pack_bundle(
                charms=charms,
                base_indeces=parsed_args.bases_index or [],
                destructive_mode=parsed_args.destructive_mode,
                overwrite=overwrite_bundle,
            )
        except (RuntimeError, CraftError) as error:
            if parsed_args.debug:
                emit.debug(f"Error when running PRIME step: {error}")
                package.launch_shell()
            raise

        if parsed_args.format:
            info = {"bundles": [str(b) for b in output_files.bundles]}
            if output_files.charms:
                info["charms"] = [str(c) for c in output_files.charms]
            emit.message(self.format_content(parsed_args.format, info))
        else:
            emit.message(f"Created {str(output_files.bundles[0])!r}.")

        if parsed_args.shell_after:
            package.launch_shell()
