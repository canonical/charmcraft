# Copyright 2020 Canonical Ltd.
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

import logging
import pathlib
import zipfile

from charmcraft.cmdbase import BaseCommand, CommandError
from .utils import load_yaml

logger = logging.getLogger(__name__)

# the minimum set of files in a bundle
MANDATORY_FILES = {'bundle.yaml'}


def build_zip(zippath, basedir, fpaths):
    """Build the final file.

    Note we convert all paths to str to support Python 3.5.
    """
    zipfh = zipfile.ZipFile(str(zippath), 'w', zipfile.ZIP_DEFLATED)
    for fpath in fpaths:
        zipfh.write(str(fpath), str(fpath.relative_to(basedir)))
    zipfh.close()


def get_paths_to_include(dirpath):
    """Get all file/dir paths to include."""
    allpaths = set()

    # all mandatory files, which must exist (currently only bundles.yaml is mandatory, and
    # it's verified before)
    for fname in MANDATORY_FILES:
        allpaths.add(dirpath / fname)

    # the extra files, which must be relative
    config = load_yaml(dirpath / 'charmcraft.yaml') or {}
    prime_specs = config.get('parts', {}).get('bundle', {}).get('prime', [])

    for spec in prime_specs:
        # check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        # config is independent of where charmcraft is running)
        if spec[0] == '/':
            raise CommandError(
                "Extra files in prime config can not be absolute: {!r}".format(spec))

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

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '-f', '--from', type=pathlib.Path, dest='from_dir',
            help="The directory where the bundle project is located, where the build "
                 "is done from; defaults to '.'")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.from_dir is None:
            dirpath = pathlib.Path.cwd()
        else:
            dirpath = parsed_args.from_dir.expanduser()
            if not dirpath.exists():
                raise CommandError("Bundle project directory was not found: '{}'.".format(dirpath))
            if not dirpath.is_dir():
                raise CommandError(
                    "Bundle project directory is not a directory: '{}'.".format(dirpath))

        # get the config files
        bundle_filepath = dirpath / 'bundle.yaml'
        bundle_config = load_yaml(bundle_filepath)
        if bundle_config is None:
            raise CommandError(
                "Missing or invalid main bundle file: '{}'.".format(bundle_filepath))
        bundle_name = bundle_config.get('name')
        if not bundle_name:
            raise CommandError(
                "Invalid bundle config; missing a 'name' field indicating the bundle's name in "
                "file '{}'.".format(bundle_filepath))

        charmcraft_filepath = dirpath / 'charmcraft.yaml'
        charmcraft_config = load_yaml(charmcraft_filepath)
        if charmcraft_config is None:
            raise CommandError(
                "Missing or invalid charmcraft file: '{}'.".format(charmcraft_filepath))
        if charmcraft_config.get('type') != 'bundle':
            raise CommandError(
                "Invalid charmcraft config; 'type' must be 'bundle' in file '{}'."
                .format(charmcraft_filepath))

        # pack everything
        paths = get_paths_to_include(dirpath)
        zipname = dirpath / (bundle_name + '.zip')
        build_zip(zipname, dirpath, paths)
        logger.info("Created '%s'.", zipname)
