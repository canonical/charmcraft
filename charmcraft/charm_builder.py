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

"""The charm package builder."""

import argparse
import errno
import logging
import os
import pathlib
import shutil
import sys
import subprocess
from typing import List

from charmcraft.cmdbase import CommandError
from charmcraft.jujuignore import JujuIgnore, default_juju_ignore
from charmcraft.utils import make_executable


# Some constants that are used through the code.
WORK_DIRNAME = "work_dir"
VENV_DIRNAME = "venv"
STAGING_VENV_DIRNAME = "staging-venv"

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

logger = logging.getLogger(__name__)


def relativise(src, dst):
    """Build a relative path from src to dst."""
    return pathlib.Path(os.path.relpath(str(dst), str(src.parent)))


class CharmBuilder:
    """The package builder."""

    def __init__(
        self,
        charmdir: pathlib.Path,
        builddir: pathlib.Path,
        entrypoint: pathlib.Path,
        allow_pip_binary: bool = None,
        python_packages: List[str] = None,
        requirements: List[str] = None,
    ):
        self.charmdir = charmdir
        self.buildpath = builddir
        self.entrypoint = entrypoint
        self.allow_pip_binary = allow_pip_binary
        self.python_packages = python_packages
        self.requirement_paths = requirements
        self.ignore_rules = self._load_juju_ignore()
        self.ignore_rules.extend_patterns([f"/{STAGING_VENV_DIRNAME}"])

    def build_charm(self) -> None:
        """Build the charm."""
        logger.debug("Building charm in %r", str(self.buildpath))

        if self.buildpath.exists():
            shutil.rmtree(str(self.buildpath))
        self.buildpath.mkdir()

        linked_entrypoint = self.handle_generic_paths()
        self.handle_dispatcher(linked_entrypoint)
        self.handle_dependencies()

    def _load_juju_ignore(self):
        ignore = JujuIgnore(default_juju_ignore)
        path = self.charmdir / ".jujuignore"
        if path.exists():
            with path.open("r", encoding="utf-8") as ignores:
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
                "Ignoring symlink because targets outside the project: %r",
                str(rel_path),
            )

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
                    logger.debug("Ignoring directory because of rules: %r", str(rel_path))
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
                    logger.debug("Ignoring file because of rules: %r", str(rel_path))
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
                    logger.debug("Ignoring file because of type: %r", str(rel_path))

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
                entrypoint_relative_path=linked_entrypoint.relative_to(self.buildpath)
            )
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
                    "Replacing existing hook %r as it's a symlink to the entrypoint",
                    node.name,
                )

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
            staging_venv_dir = self.charmdir / STAGING_VENV_DIRNAME

            # use the host environment python
            _process_run(["python3", "-m", "venv", str(staging_venv_dir)])
            pip_cmd = str(_find_venv_bin(staging_venv_dir, "pip3"))

            _process_run([pip_cmd, "--version"])

            cmd = [pip_cmd, "install", "--upgrade", "--no-binary", ":all:"]  # base command
            for reqspath in self.requirement_paths:
                cmd.append("--requirement={}".format(reqspath))  # the dependencies file(s)
            _process_run(cmd)

            # copy the virtualvenv site-packages directory to /venv in charm
            basedir = pathlib.Path(STAGING_VENV_DIRNAME)
            site_packages_dir = _find_venv_site_packages(basedir)
            shutil.copytree(site_packages_dir, self.buildpath / VENV_DIRNAME)


def _find_venv_bin(basedir, exec_base):
    """Determine the venv executable in different platforms."""
    if sys.platform == "win32":
        return basedir / "Scripts" / f"{exec_base}.exe"

    return basedir / "bin" / exec_base


def _find_venv_site_packages(basedir):
    """Determine the venv site-packages directory in different platforms."""
    output = subprocess.check_output(
        ["python3", "-c", "import sys; v=sys.version_info; print(f'{v.major} {v.minor}')"],
        text=True,
    )
    major, minor = output.strip().split(" ")

    if sys.platform == "win32":
        return basedir / f"Python{major}{minor}" / "site-packages"

    return basedir / "lib" / f"python{major}.{minor}" / "site-packages"


def _process_run(cmd: List[str]) -> None:
    """Run an external command logging its output.

    :raises CommandError: if execution crashes or ends with return code not zero.
    """
    logger.debug("Running external command %s", cmd)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
    except Exception as err:
        raise CommandError(f"Subprocess execution crashed for command {cmd}") from err

    for line in proc.stdout:
        logger.debug("   :: %s", line.rstrip())
    retcode = proc.wait()

    if retcode:
        raise CommandError(f"Subprocess command {cmd} execution failed with retcode {retcode}")


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--entrypoint",
        metavar="filename",
        default="src/charm.py",
        help="The charm entry point. Default is 'src/charm.py'.",
    )
    parser.add_argument(
        "--charmdir",
        metavar="dirname",
        default=".",
        help="The charm source directory. Default is current.",
    )
    parser.add_argument(
        "--builddir",
        metavar="dirname",
        required=True,
        help="The build destination directory",
    )
    parser.add_argument(
        "-r",
        "--requirement",
        metavar="reqfile",
        action="append",
        default=None,
        help="Comma-separated list of requirements files.",
    )

    return parser.parse_args()


def main():
    """Run the command-line interface."""
    options = _parse_arguments()

    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    logger.debug("Starting charm builder")

    builder = CharmBuilder(
        charmdir=pathlib.Path(options.charmdir),
        builddir=pathlib.Path(options.builddir),
        entrypoint=pathlib.Path(options.entrypoint),
        requirements=options.requirement,
    )
    builder.build_charm()


if __name__ == "__main__":
    main()
