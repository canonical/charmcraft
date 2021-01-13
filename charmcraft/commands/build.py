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

import errno
import logging
import os
import pathlib
import shutil
import subprocess
import zipfile

import yaml

from charmcraft.cmdbase import BaseCommand, CommandError
from charmcraft.jujuignore import JujuIgnore, default_juju_ignore
from charmcraft.utils import make_executable

logger = logging.getLogger(__name__)

# Some constants that are used through the code.
CHARM_METADATA = 'metadata.yaml'
BUILD_DIRNAME = 'build'
VENV_DIRNAME = 'venv'

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
HOOKS_DIR = 'hooks'


def _pip_needs_system():
    """Determine whether pip3 defaults to --user, needing --system to turn it off."""
    try:
        from pip.commands.install import InstallCommand
        return InstallCommand().cmd_opts.get_option('--system') is not None
    except (ImportError, AttributeError, TypeError):
        # probably not the bionic pip version then
        return False


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


def relativise(src, dst):
    """Build a relative path from src to dst."""
    return pathlib.Path(os.path.relpath(str(dst), str(src.parent)))


class Builder:
    """The package builder."""

    def __init__(self, args):
        self.charmdir = args['from']
        self.entrypoint = args['entrypoint']
        self.requirement_paths = args['requirement']

        self.buildpath = self.charmdir / BUILD_DIRNAME
        self.ignore_rules = self._load_juju_ignore()

    def run(self):
        """Build the charm."""
        logger.debug("Building charm in '%s'", self.buildpath)

        if self.buildpath.exists():
            shutil.rmtree(str(self.buildpath))
        self.buildpath.mkdir()

        linked_entrypoint = self.handle_generic_paths()
        self.handle_dispatcher(linked_entrypoint)
        self.handle_dependencies()
        zipname = self.handle_package()

        logger.info("Created '%s'.", zipname)
        return zipname

    def _load_juju_ignore(self):
        ignore = JujuIgnore(default_juju_ignore)
        path = self.charmdir / '.jujuignore'
        if path.exists():
            with path.open('r', encoding='utf-8') as ignores:
                ignore.extend_patterns(ignores)
        return ignore

    def create_symlink(self, src_path, dest_path):
        """Create a symlink in dest_path pointing relatively like src_path.

        It also verifies that the linked dir or file is inside the project.
        """
        resolved_path = src_path.resolve()
        if self.charmdir in resolved_path.parents:
            relative_link = relativise(src_path, resolved_path)
            dest_path.symlink_to(relative_link)
        else:
            rel_path = src_path.relative_to(self.charmdir)
            logger.warning(
                "Ignoring symlink because targets outside the project: '%s'", rel_path)

    def handle_generic_paths(self):
        """Handle all files and dirs except what's ignored and what will be handled later.

        Works differently for the different file types:
        - regular files: hard links
        - directories: created
        - symlinks: respected if are internal to the project
        - other types (blocks, mount points, etc): ignored
        """
        logger.debug("Linking in generic paths")

        for basedir, dirnames, filenames in os.walk(str(self.charmdir), followlinks=False):
            abs_basedir = pathlib.Path(basedir)
            rel_basedir = abs_basedir.relative_to(self.charmdir)

            # process the directories
            ignored = []
            for pos, name in enumerate(dirnames):
                rel_path = rel_basedir / name
                abs_path = abs_basedir / name

                if self.ignore_rules.match(str(rel_path), is_dir=True):
                    logger.debug("Ignoring directory because of rules: '%s'", rel_path)
                    ignored.append(pos)
                elif abs_path.is_symlink():
                    dest_path = self.buildpath / rel_path
                    self.create_symlink(abs_path, dest_path)
                else:
                    dest_path = self.buildpath / rel_path
                    dest_path.mkdir(mode=abs_path.stat().st_mode)

            # in the future don't go inside ignored directories
            for pos in reversed(ignored):
                del dirnames[pos]

            # process the files
            for name in filenames:
                rel_path = rel_basedir / name
                abs_path = abs_basedir / name

                if self.ignore_rules.match(str(rel_path), is_dir=False):
                    logger.debug("Ignoring file because of rules: '%s'", rel_path)
                elif abs_path.is_symlink():
                    dest_path = self.buildpath / rel_path
                    self.create_symlink(abs_path, dest_path)
                elif abs_path.is_file():
                    dest_path = self.buildpath / rel_path
                    try:
                        os.link(str(abs_path), str(dest_path))
                    except PermissionError:
                        # when not allowed to create hard links
                        shutil.copy2(str(abs_path), str(dest_path))
                    except OSError as e:
                        if e.errno != errno.EXDEV:
                            raise
                        shutil.copy2(str(abs_path), str(dest_path))
                else:
                    logger.debug("Ignoring file because of type: '%s'", rel_path)

        # the linked entrypoint is calculated here because it's when it's really in the build dir
        linked_entrypoint = self.buildpath / self.entrypoint.relative_to(self.charmdir)
        return linked_entrypoint

    def handle_dispatcher(self, linked_entrypoint):
        """Handle modern and classic dispatch mechanisms."""
        # dispatch mechanism, create one if wasn't provided by the project
        dispatch_path = self.buildpath / DISPATCH_FILENAME
        if not dispatch_path.exists():
            logger.debug("Creating the dispatch mechanism")
            dispatch_content = DISPATCH_CONTENT.format(
                entrypoint_relative_path=linked_entrypoint.relative_to(self.buildpath))
            with dispatch_path.open("wt", encoding="utf8") as fh:
                fh.write(dispatch_content)
                make_executable(fh)

        # bunch of symlinks, to support old juju: verify that any of the already included hooks
        # in the directory is not linking directly to the entrypoint, and also check all the
        # mandatory ones are present
        dest_hookpath = self.buildpath / HOOKS_DIR
        if not dest_hookpath.exists():
            dest_hookpath.mkdir()

        # get those built hooks that we need to replace because they are pointing to the
        # entrypoint directly and we need to fix the environment in the middle
        current_hooks_to_replace = []
        for node in dest_hookpath.iterdir():
            if node.resolve() == linked_entrypoint:
                current_hooks_to_replace.append(node)
                node.unlink()
                logger.debug(
                    "Replacing existing hook %r as it's a symlink to the entrypoint", node.name)

        # include the mandatory ones and those we need to replace
        hooknames = MANDATORY_HOOK_NAMES | {x.name for x in current_hooks_to_replace}
        for hookname in hooknames:
            logger.debug("Creating the %r hook script pointing to dispatch", hookname)
            dest_hook = dest_hookpath / hookname
            if not dest_hook.exists():
                relative_link = relativise(dest_hook, dispatch_path)
                dest_hook.symlink_to(relative_link)

    def handle_dependencies(self):
        """Handle from-directory and virtualenv dependencies."""
        logger.debug("Installing dependencies")

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
            if _pip_needs_system():
                logger.debug("adding --system to work around pip3 defaulting to --user")
                cmd.append("--system")
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
                "Charm directory is not really a directory: {!r}".format(str(dirpath)))

        self.basedir = dirpath
        return dirpath

    def validate_entrypoint(self, filepath):
        """Validate that the entrypoint exists and is executable."""
        if filepath is None:
            filepath = self.basedir / 'src' / 'charm.py'
        else:
            filepath = filepath.expanduser().absolute()

        if not filepath.exists():
            raise CommandError("Charm entry point was not found: {!r}".format(str(filepath)))
        if self.basedir not in filepath.parents:
            raise CommandError(
                "Charm entry point must be inside the project: {!r}".format(str(filepath)))
        if not os.access(str(filepath), os.X_OK):  # access does not support pathlib in 3.5
            raise CommandError(
                "Charm entry point must be executable: {!r}".format(str(filepath)))
        return filepath

    def validate_requirement(self, filepaths):
        """Validate that the given requirement(s) (if any) exist.

        If not specified, default to requirements.txt if there.
        """
        if filepaths is None:
            req = self.basedir / 'requirements.txt'
            if req.exists() and os.access(str(req), os.R_OK):  # access doesn't support pathlib 3.5
                return [req]
            return []

        filepaths = [x.expanduser().absolute() for x in filepaths]
        for fpath in filepaths:
            if not fpath.exists():
                raise CommandError("the requirements file was not found: {!r}".format(str(fpath)))
        return filepaths


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

    name = 'build'
    help_msg = "Build the charm"
    overview = _overview
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '-f', '--from', type=pathlib.Path,
            help="Charm directory with metadata.yaml where the build "
                 "takes place; defaults to '.'")
        parser.add_argument(
            '-e', '--entrypoint', type=pathlib.Path,
            help="The executable which is the operator entry point; "
                 "defaults to 'src/charm.py'")
        parser.add_argument(
            '-r', '--requirement', action='append', type=pathlib.Path,
            help="File(s) listing needed PyPI dependencies (can be used multiple "
                  "times); defaults to 'requirements.txt'")

    def run(self, parsed_args):
        """Run the command."""
        validator = Validator()
        args = validator.process(parsed_args)
        logger.debug("working arguments: %s", args)
        builder = Builder(args)
        builder.run()
