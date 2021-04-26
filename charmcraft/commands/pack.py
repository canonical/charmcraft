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

"""Infrastructure for the 'pack' command."""

import logging
import zipfile

from charmcraft.cmdbase import BaseCommand, CommandError
from charmcraft.utils import load_yaml, create_manifest

logger = logging.getLogger(__name__)

# the minimum set of files in a bundle
MANDATORY_FILES = {'bundle.yaml', 'manifest.yaml', 'README.md'}


def build_zip(zippath, basedir, fpaths):
    """Build the final file."""
    zipfh = zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED)
    for fpath in fpaths:
        zipfh.write(fpath, fpath.relative_to(basedir))
    zipfh.close()


def get_paths_to_include(config):
    """Get all file/dir paths to include."""
    dirpath = config.project.dirpath
    allpaths = set()

    # all mandatory files
    for fname in MANDATORY_FILES:
        fpath = dirpath / fname
        if not fpath.exists():
            raise CommandError("Missing mandatory file: {}.".format(fpath))
        allpaths.add(fpath)

    # the extra files (relative paths)
    for spec in config.parts:
        fpaths = sorted(fpath for fpath in dirpath.glob(spec) if fpath.is_file())
        logger.debug("Including per prime config %r: %s.", spec, fpaths)
        allpaths.update(fpaths)

    return sorted(allpaths)


_overview = """
Build the bundle and package it as a zip archive.

You can `juju deploy` the bundle .zip file or upload it to
the store (see the "upload" command).
"""


class PackCommand(BaseCommand):
    """Build the bundle or the charm.

    Eventually this command will also support charms, but for now it will work only
    on bundles.
    """

    name = 'pack'
    help_msg = "Build the bundle"
    overview = _overview
    needs_config = True

    def run(self, parsed_args):
        """Run the command."""
        # get the config files
        bundle_filepath = self.config.project.dirpath / 'bundle.yaml'
        bundle_config = load_yaml(bundle_filepath)
        if bundle_config is None:
            raise CommandError(
                "Missing or invalid main bundle file: '{}'.".format(bundle_filepath))
        bundle_name = bundle_config.get('name')
        if not bundle_name:
            raise CommandError(
                "Invalid bundle config; missing a 'name' field indicating the bundle's name in "
                "file '{}'.".format(bundle_filepath))

        # so far 'pack' works for bundles only (later this will operate also on charms)
        if self.config.type != 'bundle':
            raise CommandError(
                "Bad config: 'type' field in charmcraft.yaml must be 'bundle' for this command.")

        # pack everything
        project = self.config.project
        manifest_filepath = create_manifest(project.dirpath, project.started_at)
        try:
            paths = get_paths_to_include(self.config)
            zipname = project.dirpath / (bundle_name + '.zip')
            build_zip(zipname, project.dirpath, paths)
        finally:
            manifest_filepath.unlink()
        logger.info("Created '%s'.", zipname)
