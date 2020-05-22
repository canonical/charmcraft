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

    for line in p.stdout:
        logger.debug(":: %s", line.rstrip())
    retcode = p.wait()

    if retcode:
        logger.error("Execution ended in %d for cmd %s", retcode, cmd)
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


def build(args):
    """Main entry point."""
    charmdir = args['from']
    entrypoint = args['entrypoint']
    requirement_paths = args['requirement']

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
    cmd = [
        'pip3', 'install',  # base command
        '--system',  # indicates to use the system file structure
        '--target={}'.format(libpath),  # put all the resulting files in that specific dir
    ]
    for reqspath in requirement_paths:
        cmd.append('--requirement={}'.format(reqspath))  # the dependencies file(s)
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


class Validator:
    """A validator of all received options."""

    _options = [
        'from',  # this needs to be processed first, as it's a base dir to find other files
        'entrypoint',
        'requirement',
    ]

    def __init__(self):
        self.basedir = None  # this will be fulfilled when processing 'from'

    def process(self, parsed_args):
        """Process the received options."""
        result = {}
        for opt in self._options:
            meth = getattr(self, 'validate_' + opt)
            result[opt] = meth(getattr(parsed_args, opt, None))
        return result

    def validate_from(self, arg):
        """Validate that the charm dir is there and yes, a directory."""
        if arg is None:
            arg = '.'
        arg = pathlib.Path(arg).expanduser()

        if not arg.exists():
            raise CommandError("the charm directory was not found: {!r}".format(str(arg)))
        if not arg.is_dir():
            raise CommandError(
                "the charm directory is not really a directory: {!r}".format(str(arg)))

        self.basedir = arg
        return arg

    def validate_entrypoint(self, arg):
        """Validate that the entrypoint exists and is executable."""
        if arg is None:
            arg = self.basedir / 'src' / 'charm.py'
        arg = pathlib.Path(arg).expanduser()

        if not arg.exists():
            raise CommandError("the charm entry point was not found: {!r}".format(str(arg)))
        if not os.access(arg, os.X_OK):
            raise CommandError("the charm entry point must be executable: {!r}".format(str(arg)))
        return arg

    def validate_requirement(self, arg):
        """Validate that the given requirement(s) (if any) exist.

        If not specified, default to requirements.txt if there.
        """
        if arg is None:
            arg = self.basedir / 'requirements.txt'
            if arg.exists() and os.access(arg, os.R_OK):
                return [arg]
            return []

        arg = [pathlib.Path(x) for x in arg]
        for fpath in arg:
            if not fpath.exists():
                raise CommandError("the requirements file was not found: {!r}".format(str(fpath)))
        return arg


class BuildCommand(BaseCommand):
    """Show the version."""
    name = 'build'
    help_msg = "build the charm"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '-f', '--from',
            help="the directory where the charm project is located, from where the build "
                 "is done; defaults to '.'")
        parser.add_argument(
            '-e', '--entrypoint',
            help="the executable script or program which is the entry point to all the "
                 "charm code; defaults to 'src/charm.py'")
        parser.add_argument(
            '-r', '--requirement', action='append',
            help="the file(s) with the needed dependencies (this option can be used multiple "
                  "times); defaults to 'requirements.txt'")

    def run(self, parsed_args):
        """Run the command."""
        validator = Validator()
        args = validator.process(parsed_args)
        logger.debug("working arguments: %s", args)
        build(args)
