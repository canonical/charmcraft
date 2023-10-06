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

"""The charm package builder.

This is a standalone script run by the Charm Plugin.
"""

import argparse
import errno
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
from typing import List

from charmcraft import instrum
from charmcraft.const import (
    DEPENDENCIES_HASH_FILENAME,
    DISPATCH_CONTENT,
    DISPATCH_FILENAME,
    HOOKS_DIRNAME,
    MANDATORY_HOOK_NAMES,
    STAGING_VENV_DIRNAME,
    VENV_DIRNAME,
)
from charmcraft.env import get_charm_builder_metrics_path
from charmcraft.errors import DependencyError
from charmcraft.jujuignore import JujuIgnore, default_juju_ignore
from charmcraft.utils import (
    collect_charmlib_pydeps,
    get_pip_command,
    get_pip_version,
    get_requirements_file_package_names,
    make_executable,
    validate_strict_dependencies,
)

MINIMUM_PIP_VERSION = (22, 0)
KNOWN_GOOD_PIP_URL = "https://files.pythonhosted.org/packages/ba/19/e63fb4e0d20e48bd2167bb7e857abc0e21679e24805ba921a224df8977c0/pip-23.2.1.tar.gz"


def relativise(src, dst):
    """Build a relative path from src to dst."""
    return pathlib.Path(os.path.relpath(str(dst), str(src.parent)))


class CharmBuilder:
    """The package builder."""

    def __init__(
        self,
        builddir: pathlib.Path,
        installdir: pathlib.Path,
        entrypoint: pathlib.Path,
        allow_pip_binary: bool = None,
        binary_python_packages: List[str] = None,
        python_packages: List[str] = None,
        requirements: List[pathlib.Path] = None,
        strict_dependencies: bool = False,
    ) -> None:
        self.builddir = builddir
        self.installdir = installdir
        self.entrypoint = entrypoint
        self.allow_pip_binary = allow_pip_binary
        self.binary_python_packages = binary_python_packages
        self.python_packages = python_packages
        self.requirement_paths = requirements
        self.strict_dependencies = strict_dependencies
        self.ignore_rules = self._load_juju_ignore()
        self.ignore_rules.extend_patterns([f"/{STAGING_VENV_DIRNAME}"])

        self.charmlib_deps = collect_charmlib_pydeps(builddir)
        print("Collected charmlib dependencies:", self.charmlib_deps)

    def build_charm(self) -> None:
        """Build the charm."""
        print(f"Building charm in {str(self.installdir)!r}")

        if self.installdir.exists():
            shutil.rmtree(str(self.installdir))
        self.installdir.mkdir()

        linked_entrypoint = self.handle_generic_paths()
        self.handle_dispatcher(linked_entrypoint)
        self.handle_dependencies()

    def _load_juju_ignore(self):
        ignore = JujuIgnore(default_juju_ignore)
        path = self.builddir / ".jujuignore"
        if path.exists():
            with path.open("r", encoding="utf-8") as ignores:
                ignore.extend_patterns(ignores)
        return ignore

    def create_symlink(self, src_path, dest_path):
        """Create a symlink in dest_path pointing relatively like src_path.

        It also verifies that the linked dir or file is inside the project.
        """
        resolved_path = src_path.resolve()
        if self.builddir in resolved_path.parents:
            relative_link = relativise(src_path, resolved_path)
            dest_path.symlink_to(relative_link)
        else:
            rel_path = src_path.relative_to(self.builddir)
            print(f"Ignoring symlink because targets outside the project: {str(rel_path)!r}")

    @instrum.Timer("Handling generic paths")
    def handle_generic_paths(self):
        """Handle all files and dirs except what's ignored and what will be handled later.

        Works differently for the different file types:
        - regular files: hard links
        - directories: created
        - symlinks: respected if are internal to the project
        - other types (blocks, mount points, etc): ignored
        """
        print("Linking in generic paths")

        for basedir, dirnames, filenames in os.walk(str(self.builddir), followlinks=False):
            abs_basedir = pathlib.Path(basedir)
            rel_basedir = abs_basedir.relative_to(self.builddir)

            # process the directories
            ignored = []
            for pos, name in enumerate(dirnames):
                rel_path = rel_basedir / name
                abs_path = abs_basedir / name

                if self.ignore_rules.match(str(rel_path), is_dir=True):
                    print(f"Ignoring directory because of rules: {str(rel_path)!r}")
                    ignored.append(pos)
                elif abs_path.is_symlink():
                    dest_path = self.installdir / rel_path
                    self.create_symlink(abs_path, dest_path)
                else:
                    dest_path = self.installdir / rel_path
                    dest_path.mkdir(mode=abs_path.stat().st_mode)

            # in the future don't go inside ignored directories
            for pos in reversed(ignored):
                del dirnames[pos]

            # process the files
            for name in filenames:
                rel_path = rel_basedir / name
                abs_path = abs_basedir / name

                if self.ignore_rules.match(str(rel_path), is_dir=False):
                    print(f"Ignoring file because of rules: {str(rel_path)!r}")
                elif abs_path.is_symlink():
                    dest_path = self.installdir / rel_path
                    self.create_symlink(abs_path, dest_path)
                elif abs_path.is_file():
                    dest_path = self.installdir / rel_path
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
                    print(f"Ignoring file because of type: {str(rel_path)!r}")

        # the linked entrypoint is calculated here because it's when it's really in the build dir
        return self.installdir / self.entrypoint.relative_to(self.builddir)

    @instrum.Timer("Handling dispatcher")
    def handle_dispatcher(self, linked_entrypoint):
        """Handle modern and classic dispatch mechanisms."""
        # dispatch mechanism, create one if wasn't provided by the project
        dispatch_path = self.installdir / DISPATCH_FILENAME
        if not dispatch_path.exists():
            print("Creating the dispatch mechanism")
            dispatch_content = DISPATCH_CONTENT.format(
                entrypoint_relative_path=linked_entrypoint.relative_to(self.installdir)
            )
            with dispatch_path.open("wt", encoding="utf8") as fh:
                fh.write(dispatch_content)
                make_executable(fh)

        # bunch of symlinks, to support old juju: verify that any of the already included hooks
        # in the directory is not linking directly to the entrypoint, and also check all the
        # mandatory ones are present
        dest_hookpath = self.installdir / HOOKS_DIRNAME
        if not dest_hookpath.exists():
            dest_hookpath.mkdir()

        # get those built hooks that we need to replace because they are pointing to the
        # entrypoint directly and we need to fix the environment in the middle
        current_hooks_to_replace = []
        for node in dest_hookpath.iterdir():
            if node.resolve() == linked_entrypoint:
                current_hooks_to_replace.append(node)
                node.unlink()
                print(f"Replacing existing hook {node.name!r} as it's a symlink to the entrypoint")

        # include the mandatory ones and those we need to replace
        hooknames = MANDATORY_HOOK_NAMES | {x.name for x in current_hooks_to_replace}
        for hookname in hooknames:
            print(f"Creating the {hookname!r} hook script pointing to dispatch")
            dest_hook = dest_hookpath / hookname
            if not dest_hook.exists():
                relative_link = relativise(dest_hook, dispatch_path)
                dest_hook.symlink_to(relative_link)

    def _calculate_dependencies_hash(self):
        """Calculate a hash for all current dependencies."""
        all_deps = []
        for req_file in self.requirement_paths:
            all_deps.append(req_file.read_text())
        all_deps.extend(self.binary_python_packages)
        all_deps.extend(self.python_packages)
        all_deps.extend(self.charmlib_deps)
        deps_mashup = "".join(map(repr, all_deps))
        return hashlib.sha1(deps_mashup.encode("utf8")).hexdigest()

    @instrum.Timer("Installing dependencies")
    def _install_dependencies(self, staging_venv_dir):
        """Install all dependencies in a specific directory."""
        # create virtualenv using the host environment python
        with instrum.Timer("Creating venv"):
            _process_run(["python3", "-m", "venv", str(staging_venv_dir)])
        pip_cmd = str(_find_venv_bin(staging_venv_dir, "pip"))

        with instrum.Timer("Ensuring a recent enough pip..."):
            # pip 20 (included with focal) has dependency resolution issues related to
            # common charm dependencies (e.g. ops). Resolve this by updating to a
            # known working version of pip.
            if get_pip_version(pip_cmd) < MINIMUM_PIP_VERSION:
                _process_run([pip_cmd, "install", f"pip@{KNOWN_GOOD_PIP_URL}"])

        with instrum.Timer("Installing all dependencies"):
            if self.strict_dependencies:
                self._install_strict_dependencies(pip_cmd)
                return

            # Legacy non-strict dependencies.
            # This method is not valid for any bases added after 2024-01-01 or for DEVEL bases.
            try:
                _process_run(
                    get_pip_command(
                        [pip_cmd, "install"],
                        self.requirement_paths,
                        source_deps=[*self.python_packages, *self.charmlib_deps],
                        binary_deps=self.binary_python_packages,
                    )
                )
            except RuntimeError:
                print(
                    "WARNING: Initial package installation failed. "
                    "Falling back to older method, which may leave your charm "
                    "in an un-runnable state."
                )
                if self.binary_python_packages:
                    # install python packages, allowing binary packages
                    cmd = [pip_cmd, "install", "--upgrade"]  # base command
                    cmd.extend(self.binary_python_packages)  # the python packages to install
                    _process_run(cmd)
                if self.python_packages:
                    # install python packages from source
                    cmd = [pip_cmd, "install", "--upgrade", "--no-binary", ":all:"]  # base command
                    cmd.extend(self.python_packages)  # the python packages to install
                    _process_run(cmd)
                if self.requirement_paths:
                    # install dependencies from requirement files
                    cmd = [pip_cmd, "install", "--upgrade", "--no-binary", ":all:"]  # base command
                    for reqspath in self.requirement_paths:
                        cmd.append(f"--requirement={reqspath}")  # the dependencies file(s)
                    _process_run(cmd)
                if self.charmlib_deps:
                    # install charmlibs python dependencies
                    cmd = [pip_cmd, "install", "--upgrade", "--no-binary", ":all:"]  # base command
                    cmd.extend(self.charmlib_deps)  # the python packages to install
                _process_run(cmd)

    def _install_strict_dependencies(self, pip_cmd: str) -> None:
        if not self.requirement_paths:
            raise DependencyError(
                "No requirements files have been passed to the charm builder.",
                details="Strict dependencies mode needs at least one requirements file.",
            )
        validate_strict_dependencies(
            get_requirements_file_package_names(*self.requirement_paths),
            self.charmlib_deps,
            self.python_packages or [],
            self.binary_python_packages or [],
        )
        _process_run(
            get_pip_command(
                [pip_cmd, "install"],
                self.requirement_paths,
                binary_deps=self.binary_python_packages or [],
            )
        )

    def handle_dependencies(self):
        """Handle from-directory and virtualenv dependencies."""
        print("Handling dependencies")
        if not (
            self.requirement_paths
            or self.binary_python_packages
            or self.python_packages
            or self.charmlib_deps
        ):
            print("No dependencies to handle")
            return

        staging_venv_dir = self.builddir / STAGING_VENV_DIRNAME
        hash_file = self.builddir / DEPENDENCIES_HASH_FILENAME

        # find out if current dependencies are the same than the last run.
        current_deps_hash = self._calculate_dependencies_hash()
        print(f"Current dependencies hash: {current_deps_hash!r}")
        if not staging_venv_dir.exists():
            print("Dependencies directory not found")
            same_dependencies = False
        elif hash_file.exists():
            try:
                previous_deps_hash = hash_file.read_text(encoding="utf8")
            except Exception as exc:
                print(f"Problems reading the dependencies hash file: {exc}")
                same_dependencies = False
            else:
                print(f"Previous dependencies hash: {previous_deps_hash!r}")
                same_dependencies = previous_deps_hash == current_deps_hash
        else:
            print("Dependencies hash file not found")
            same_dependencies = False

        if same_dependencies:
            print("Reusing installed dependencies, they are equal to last run ones")
        else:
            print("Installing dependencies")
            self._install_dependencies(staging_venv_dir)

            # save the hash file after all successful installations
            hash_file.write_text(current_deps_hash, encoding="utf8")

        # always copy the virtualvenv site-packages directory to /venv in charm
        basedir = pathlib.Path(STAGING_VENV_DIRNAME)
        site_packages_dir = _find_venv_site_packages(basedir)
        shutil.copytree(site_packages_dir, self.installdir / VENV_DIRNAME)


def _find_venv_bin(basedir: pathlib.Path, exec_base: str) -> pathlib.Path:
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

    :raises CraftError: if execution crashes or ends with return code not zero.
    """
    print(f"Running external command {cmd}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Subprocess command {cmd} execution crashed: {exc!r}")

    for line in proc.stdout:
        print(f"   :: {line.rstrip()}")
    retcode = proc.wait()

    if retcode:
        raise RuntimeError(f"Subprocess command {cmd} execution failed with retcode {retcode}")


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--entrypoint",
        default="src/charm.py",
        type=pathlib.Path,
        help="The charm entry point. Default is 'src/charm.py'.",
    )
    parser.add_argument(
        "--builddir",
        default=".",
        type=pathlib.Path,
        help="The charm source directory. Default is current.",
    )
    parser.add_argument(
        "--installdir",
        required=True,
        type=pathlib.Path,
        help="The build destination directory",
    )
    parser.add_argument(
        "-b",
        "--binary-package",
        action="append",
        help="Binary Python package to install before requirements.",
    )
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "-p",
        "--package",
        action="append",
        help="Python package to install before requirements.",
    )
    strict_group.add_argument(
        "--strict-dependencies", action="store_true", help="Use strict dependencies."
    )
    parser.add_argument(
        "-r",
        "--requirement",
        action="append",
        type=pathlib.Path,
        help="Requirements file to install dependencies from.",
    )

    return parser.parse_args()


def main():
    """Run the command-line interface."""
    options = _parse_arguments()

    print("Starting charm builder")
    builder = CharmBuilder(
        builddir=options.builddir,
        installdir=options.installdir,
        entrypoint=options.entrypoint,
        binary_python_packages=options.binary_package or [],
        python_packages=options.package or [],
        requirements=options.requirement or [],
        strict_dependencies=options.strict_dependencies,
    )
    builder.build_charm()


if __name__ == "__main__":
    with instrum.Timer("Full charm_builder.py main"):
        main()
    instrum.dump(get_charm_builder_metrics_path())
