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

import yaml

from charmcraft.cmdbase import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Some constants that are used through the code.
CHARM_METADATA = 'metadata.yaml'
BUILD_DIRNAME = 'build'
VENV_DIRNAME = 'venv'

# copy these if they exist
CHARM_OPTIONAL = [
    'config.yaml',
    'metrics.yaml',
    'actions.yaml',
    'lxd-profile.yaml',
    'version'
]

# The file name and template for the dispatch script
DISPATCH_FILENAME = 'dispatch'
# If Juju doesn't support the dispatch mechanism, it will execute the
# hook, and we'd need sys.argv[0] to be the name of the hook but it's
# geting lost by calling this dispatch, so we fake JUJU_DISPATCH_PATH
# to be the value it would've otherwise been.
DISPATCH_CONTENT = """#!/bin/sh

JUJU_DISPATCH_PATH="${{JUJU_DISPATCH_PATH:-$0}}" PYTHONPATH=lib:venv ./{entrypoint_relative_path}
"""

# The minimum set of hooks to be provided for compatibility with old Juju
MANDATORY_HOOK_NAMES = {'install', 'start', 'upgrade-charm'}


def polite_exec(cmd):
    """Execute a command, only showing output if error."""
    logger.debug("Running external command %s", cmd)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    except Exception as err:
        logger.error("Executing %s crashed with %r", cmd, err)
        return 1

    for line in proc.stdout:
        logger.debug(":: %s", line.rstrip())
    retcode = proc.wait()

    if retcode:
        logger.error("Executing %s failed with return code %d", cmd, retcode)
    return retcode


class Builder:
    """The package builder."""

    def __init__(self, args):
        self.charmdir = args['from']
        self.entrypoint = args['entrypoint']
        self.requirement_paths = args['requirement']

        self.buildpath = self.charmdir / BUILD_DIRNAME

    def run(self):
        """Main building process."""
        logger.debug("Building charm in %r", str(self.buildpath))

        if self.buildpath.exists():
            shutil.rmtree(str(self.buildpath))
        self.buildpath.mkdir()

        linked_entrypoint = self.handle_code()
        self.handle_dispatcher(linked_entrypoint)
        self.handle_dependencies()
        zipname = self.handle_package()

        logger.info("Done, charm left in %r", zipname)
        return zipname

    def _link_to_buildpath(self, srcpath):
        """Link a file to the build directory."""
        destpath = self.buildpath / srcpath.name
        destpath.symlink_to(srcpath)
        return destpath

    def handle_code(self):
        """Handle basic files and the charm source code."""
        # basic files
        logger.debug("Linking in basic files and charm code")
        self._link_to_buildpath(self.charmdir / CHARM_METADATA)
        for fn in CHARM_OPTIONAL:
            path = self.charmdir / fn
            if path.exists():
                self._link_to_buildpath(path)

        # the whole dir/tree if entry point is in a project's subdir, itself alone otherwise
        if self.charmdir in self.entrypoint.parents and self.charmdir != self.entrypoint.parent:
            # link the whole dir
            linked_subdir = self._link_to_buildpath(self.entrypoint.parent)
            linked_entrypoint = linked_subdir / self.entrypoint.name
        else:
            # just the entry point
            linked_entrypoint = self._link_to_buildpath(self.entrypoint)

        return linked_entrypoint

    def handle_dispatcher(self, linked_entrypoint):
        """Handle modern and classic dispatch mechanisms."""
        # dispatch mechanism
        current_dispatch = self.charmdir / DISPATCH_FILENAME
        if current_dispatch.exists():
            logger.debug("Including the current dispatch script")
            dispatch_path = self._link_to_buildpath(current_dispatch)
        else:
            logger.debug("Creating the dispatch mechanism")
            dispatch_content = DISPATCH_CONTENT.format(
                entrypoint_relative_path=linked_entrypoint.relative_to(self.buildpath))
            dispatch_path = self.buildpath / DISPATCH_FILENAME
            with dispatch_path.open("wt", encoding="utf8") as fh:
                fh.write(dispatch_content)
                fileno = fh.fileno()
                os.fchmod(fileno, os.fstat(fileno).st_mode | stat.S_IXUSR)

        # bunch of symlinks, to support old juju; whatever is in the charm's hooks directory
        # is respected, but also the mandatory ones are created if missing
        current_hookpath = self.charmdir / 'hooks'
        dest_hookpath = self.buildpath / 'hooks'
        dest_hookpath.mkdir()
        if current_hookpath.exists():
            current_hooks = list(current_hookpath.iterdir())
        else:
            current_hooks = []

        # respect current nodes
        for current_hook in current_hooks:
            logger.debug("Including current %r hook", current_hook.name)
            dest_hook = dest_hookpath / current_hook.name
            dest_hook.symlink_to(current_hook)

        # include mandatory ones if missing
        missing_mandatory = MANDATORY_HOOK_NAMES - {x.name for x in current_hooks}
        for hookname in missing_mandatory:
            logger.debug("Creating the %r hook script pointing to dispatch", hookname)
            dest_hook = dest_hookpath / hookname
            dest_hook.symlink_to(dispatch_path)

    def handle_dependencies(self):
        """Handle from-directory and virtualenv dependencies."""
        logger.debug("Installing dependencies")

        # whole-dirs dependencies
        for depdir in ('lib', 'mod'):
            from_dir = self.charmdir / depdir
            if from_dir.exists():
                self._link_to_buildpath(from_dir)

        # virtualenv with other dependencies (if any)
        if self.requirement_paths:
            retcode = polite_exec(['pip3', 'list'])
            if retcode:
                raise CommandError("problems using pip")

            venvpath = self.buildpath / VENV_DIRNAME
            cmd = [
                'pip3', 'install',  # base command
                '--target={}'.format(venvpath),  # put all the resulting files in that specific dir
            ]
            for reqspath in self.requirement_paths:
                cmd.append('--requirement={}'.format(reqspath))  # the dependencies file(s)
            retcode = polite_exec(cmd)
            if retcode:
                raise CommandError("problems installing dependencies")

    def handle_package(self):
        """Handle the final package creation."""
        logger.debug("Parsing the project's metadata")
        with (self.charmdir / CHARM_METADATA).open('rt', encoding='utf8') as fh:
            metadata = yaml.safe_load(fh)

        logger.debug("Creating the package itself")
        zipname = metadata['name'] + '.charm'
        zipfh = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
        buildpath_str = str(self.buildpath)  # os.walk does not support pathlib in 3.5
        for dirpath, dirnames, filenames in os.walk(buildpath_str, followlinks=True):
            dirpath = pathlib.Path(dirpath)
            for filename in filenames:
                filepath = dirpath / filename
                zipfh.write(str(filepath), str(filepath.relative_to(self.buildpath)))

        zipfh.close()
        return zipname


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
        arg = pathlib.Path(arg).expanduser().absolute()

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
        arg = pathlib.Path(arg).expanduser().absolute()

        if not arg.exists():
            raise CommandError("the charm entry point was not found: {!r}".format(str(arg)))
        if not os.access(str(arg), os.X_OK):  # access does not support pathlib in 3.5
            raise CommandError("the charm entry point must be executable: {!r}".format(str(arg)))
        return arg

    def validate_requirement(self, arg):
        """Validate that the given requirement(s) (if any) exist.

        If not specified, default to requirements.txt if there.
        """
        if arg is None:
            arg = self.basedir / 'requirements.txt'
            if arg.exists() and os.access(str(arg), os.R_OK):  # access doesn't support pathlib 3.5
                return [arg]
            return []

        arg = [pathlib.Path(x).expanduser().absolute() for x in arg]
        for fpath in arg:
            if not fpath.exists():
                raise CommandError("the requirements file was not found: {!r}".format(str(fpath)))
        return arg


class BuildCommand(BaseCommand):
    """Build the charm."""
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
        builder = Builder(args)
        builder.run()
