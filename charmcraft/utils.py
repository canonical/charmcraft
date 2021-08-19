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

"""Collection of utilities for charmcraft."""

import os
import pathlib
import platform
import sys
from collections import namedtuple
from dataclasses import dataclass
from stat import S_IRGRP, S_IROTH, S_IRUSR, S_IXGRP, S_IXOTH, S_IXUSR

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined

from charmcraft.cmdbase import CommandError
from charmcraft.env import is_charmcraft_running_in_managed_mode
from charmcraft.poc_messages_lib import emit


OSPlatform = namedtuple("OSPlatform", "system release machine")

# handy masks for execution and reading for everybody
S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH
S_IRALL = S_IRUSR | S_IRGRP | S_IROTH

# translations from what the platform module informs to the term deb and
# snaps actually use
ARCH_TRANSLATIONS = {
    "aarch64": "arm64",
    "armv7l": "armhf",
    "i686": "i386",
    "ppc": "powerpc",
    "ppc64le": "ppc64el",
    "x86_64": "amd64",
}


def make_executable(fh):
    """Make open file fh executable."""
    fileno = fh.fileno()
    mode = os.fstat(fileno).st_mode
    mode_r = mode & S_IRALL
    mode_x = mode_r >> 2
    mode = mode | mode_x
    os.fchmod(fileno, mode)


def load_yaml(fpath):
    """Return the content of a YAML file."""
    if not fpath.is_file():
        emit.trace(f"Couldn't find config file {str(fpath)!r}")
        return
    try:
        with fpath.open("rb") as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        emit.error(f"Failed to read/parse config file {str(fpath)!r}: {err!r}")
        return
    return content


def get_templates_environment(templates_dir):
    """Create and return a Jinja environment to deal with the templates."""
    env = Environment(
        loader=PackageLoader("charmcraft", "templates/{}".format(templates_dir)),
        autoescape=False,  # no need to escape things here :-)
        keep_trailing_newline=True,  # they're not text files if they don't end in newline!
        optimized=False,  # optimization doesn't make sense for one-offs
        undefined=StrictUndefined,
    )  # fail on undefined
    return env


class SingleOptionEnsurer:
    """Argparse helper to ensure that the option is specified only once, converting it properly.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('-n', '--number',  type=SingleOptionEnsurer(int), required=True)

    No lower limit is checked, that is verified with required=True in the argparse definition.
    """

    def __init__(self, converter):
        self.converter = converter
        self.count = 0

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        self.count += 1
        if self.count > 1:
            raise ValueError("the option can be specified only once")
        return self.converter(value)


@dataclass(frozen=True)
class ResourceOption:
    """Argparse helper to validate and convert a 'resource' option.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('--resource',  type=ResourceOption())
    """

    name: str = None
    revision: int = None

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        parts = [x.strip() for x in value.split(":")]
        parts = [p for p in parts if p]
        if len(parts) == 2:
            name, revision = parts
            try:
                revision = int(revision)
            except ValueError:
                pass
            else:
                if revision > 0:
                    return ResourceOption(name, revision)
        msg = "the resource format must be <name>:<revision> (revision being a positive integer)"
        raise ValueError(msg)


def useful_filepath(filepath):
    """Return a valid Path with user name expansion for filepath.

    CommandError is raised if filepath is not a valid file or is not readable.
    """
    filepath = pathlib.Path(filepath).expanduser()
    if not os.access(filepath, os.R_OK):
        raise CommandError("Cannot access {!r}.".format(str(filepath)))
    if not filepath.is_file():
        raise CommandError("{!r} is not a file.".format(str(filepath)))
    return filepath


def get_os_platform(filepath=pathlib.Path("/etc/os-release")):
    """Determine a system/release combo for an OS using /etc/os-release if available."""
    system = platform.system()
    release = platform.release()
    machine = platform.machine()

    if system == "Linux":
        try:
            with filepath.open("rt", encoding="utf-8") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            emit.trace("Unable to locate 'os-release' file, using default values")
        else:
            os_release = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.rstrip().split("=", 1)
                if value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                os_release[key] = value
            system = os_release.get("ID", system)
            release = os_release.get("VERSION_ID", release)

    return OSPlatform(system=system, release=release, machine=machine)


def get_host_architecture():
    """Get host architecture in deb format suitable for base definition."""
    os_platform = get_os_platform()
    return ARCH_TRANSLATIONS.get(os_platform.machine, os_platform.machine)


def confirm_with_user(prompt, default=False) -> bool:
    """Query user for yes/no answer.

    If stdin is not a tty, the default value is returned.

    If user returns an empty answer, the default value is returned.
    returns default value.

    :returns: True if answer starts with [yY], False if answer starts with [nN],
        otherwise the default.
    """
    if is_charmcraft_running_in_managed_mode():
        raise RuntimeError("confirmation not yet supported in managed-mode")

    if not sys.stdin.isatty():
        return default

    choices = " [Y/n]: " if default else " [y/N]: "

    reply = str(input(prompt + choices)).lower().strip()
    if reply and reply[0] == "y":
        return True
    elif reply and reply[0] == "n":
        return False
    else:
        return default
