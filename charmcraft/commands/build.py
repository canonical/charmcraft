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
import os
import pathlib
import shutil
import stat
import subprocess
import zipfile

from charmcraft.cmdbase import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Some constants that are used through the code.
CHARM_METADATA = 'metadata.yaml'
BUILD_DIRNAME = 'build'
DISPATCH_FILENAME = 'dispatch'

# The template for the dispatch script
DISPATCH = """#!/bin/sh

PYTHONPATH=lib {entrypoint_relative_path}
"""

# The minimum set of hooks to be provided for compatibility with old Juju
HOOK_NAMES = [
    'install',
    'start',
    'upgrade-charm',
]


def polite_exec(cmd):
    """Execute a command, only showing output if error."""
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    stdout = []
    for line in p.stdout:
        stdout.append(line)
    retcode = p.wait()

    if retcode:
        logger.error("Execution ended in %d for cmd %s", retcode, cmd)
        for line in stdout:
            logger.debug(":: %s", line.rstrip())
    return retcode


def link(srcpath, destdir):
    """Link a file."""
    if not destdir.exists():
        os.makedirs(destdir)

    # XXX Facundo 2020-05-19: we could make hard links here, with the benefit of `juju deploy`
    # being happy about these links, while at the same time getting the benefit of "changing
    # a file in the project and being ready to deploy" (however, TRICKY!); that said, we would
    # need to handle directories by hand (but currently we're not linking dirs...)
    destpath = destdir / srcpath.name
    destpath.symlink_to(srcpath)
    return destpath


def _build(charmdir, entrypoint):
    """Main entry point."""
    buildpath = charmdir / BUILD_DIRNAME
    logger.debug("Building charm in %r", str(buildpath))

    # XXX Facundo 2020-05-18: for now we're re-building always from scratch, in the
    # future we *may* reuse stuff already inside
    if buildpath.exists():
        shutil.rmtree(str(buildpath))
    buildpath.mkdir()

    # basic files
    logger.debug("Linking in basic files and charm code")
    link(charmdir / CHARM_METADATA, buildpath)

    # the charm code
    # XXX Facundo 2020-05-18: for now, one file, may we copy the entrypoint and its whole dir/tree
    # (if not charmdir); also we need to understand if we want to ignore some files (e.g. .pyc)
    linked_entrypoint = link(entrypoint, buildpath / 'src')

    # dispatch mechanism
    logger.debug("Creating the dispatch mechanism")
    dispatch_content = DISPATCH.format(
        entrypoint_relative_path=linked_entrypoint.relative_to(buildpath))
    dispatch_path = buildpath / DISPATCH_FILENAME
    with open(dispatch_path, "wt", encoding="utf8") as fh:
        fh.write(dispatch_content)
    os.chmod(dispatch_path, dispatch_path.stat().st_mode | stat.S_IXUSR)

    # bunch of symlinks, to support old juju
    hookpath = buildpath / 'hooks'
    hookpath.mkdir()
    for hookname in HOOK_NAMES:
        (hookpath / hookname).symlink_to(dispatch_path)

    # dependencies
    logger.debug("Installing dependencies")
    # XXX Facundo 2020-05-18: we may want to be flexible with how to include the
    # dependencies, e.g. respecting current lib directory, or not having a requirements file
    libpath = buildpath / 'lib'
    reqspath = charmdir / 'requirements.txt'
    cmd = [
        'pip3', 'install',  # base command
        '--system',  # indicates to use the system file structure
        '--target={}'.format(libpath),  # put all the resulting files in that specific dir
        '--requirement={}'.format(reqspath),  # the dependencies file
    ]
    retcode = polite_exec(cmd)
    if retcode:
        raise CommandError("problems installing the dependencies")

    # z-z-zip it!
    logger.debug("Creating the package itself")
    zipname = charmdir.name + '.charm'
    zipfh = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    for dirpath, dirnames, filenames in os.walk(buildpath):
        dirpath = pathlib.Path(dirpath)
        for filename in filenames:
            filepath = dirpath / filename
            zipfh.write(str(filepath), str(filepath.relative_to(buildpath)))

    zipfh.close()
    logger.info("Done, charm left in %r", zipname)


class BuildCommand(BaseCommand):
    """Show the version."""
    name = 'build'
    help_msg = "build the charm"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'charmdir', metavar='charm-dir',
            help='The directory where the charm project is located')
        parser.add_argument(
            'entrypoint', metavar='charm-entrypoint',
            help='The executable script or program which is the entry point to all the charm code')

    def run(self, parsed_args):
        """Run the command."""
        charmdir = pathlib.Path(parsed_args.charmdir)
        if not charmdir.exists():
            raise CommandError(
                "indicated charm directory not found: {!r}".format(parsed_args.charmdir))
        if not charmdir.is_dir():
            raise CommandError(
                "indicated charm directory is not a directory: {!r}".format(parsed_args.charmdir))

        entrypoint = pathlib.Path(parsed_args.entrypoint)
        if not entrypoint.exists():
            raise CommandError(
                "indicated charm entry point not found: {!r}".format(parsed_args.entrypoint))
        if not os.access(entrypoint, os.X_OK):
            raise CommandError(
                "indicated charm entry point must be executable: {!r}".format(
                    parsed_args.entrypoint))

        _build(charmdir, entrypoint)
