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

import logging
import os
import pathlib
import platform
from collections import namedtuple
from stat import S_IXUSR, S_IXGRP, S_IXOTH, S_IRUSR, S_IRGRP, S_IROTH

import attr
import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined

from charmcraft import __version__
from charmcraft.cmdbase import CommandError

logger = logging.getLogger('charmcraft.commands')

OSPlatform = namedtuple("OSPlatform", "system release machine")

# handy masks for execution and reading for everybody
S_IXALL = S_IXUSR | S_IXGRP | S_IXOTH
S_IRALL = S_IRUSR | S_IRGRP | S_IROTH

# translations from what the platform module informs to the term deb and
# snaps actually use
ARCH_TRANSLATIONS = {
    'aarch64': 'arm64',
    'armv7l': 'armhf',
    'i686': 'i386',
    'ppc': 'powerpc',
    'ppc64le': 'ppc64el',
    'x86_64': 'amd64',
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
        logger.debug("Couldn't find config file %s", fpath)
        return
    try:
        with fpath.open('rb') as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        logger.error("Failed to read/parse config file %s: %r", fpath, err)
        return
    return content


def get_templates_environment(templates_dir):
    """Create and return a Jinja environment to deal with the templates."""
    env = Environment(
        loader=PackageLoader('charmcraft', 'templates/{}'.format(templates_dir)),
        autoescape=False,            # no need to escape things here :-)
        keep_trailing_newline=True,  # they're not text files if they don't end in newline!
        optimized=False,             # optimization doesn't make sense for one-offs
        undefined=StrictUndefined)   # fail on undefined
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


@attr.s(frozen=True)
class ResourceOption:
    """Argparse helper to validate and convert a 'resource' option.

    Receives a callable to convert the string from command line to the desired object.

    Example of use:

        parser.add_argument('--resource',  type=ResourceOption())
    """

    name = attr.ib(default=None)
    revision = attr.ib(default=None)

    def __call__(self, value):
        """Run by argparse to validate and convert the given argument."""
        parts = [x.strip() for x in value.split(':')]
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
    if not os.access(str(filepath), os.R_OK):  # access doesn't support pathlib in 3.5
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
            with filepath.open("rt", encoding='utf-8') as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            logger.debug("Unable to locate 'os-release' file, using default values")
        else:
            os_release = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.rstrip().split("=", 1)
                if value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                os_release[key] = value
            system = os_release.get("NAME", system)
            release = os_release.get("VERSION_ID", release)

    return OSPlatform(system=system, release=release, machine=machine)


def create_manifest(basedir, started_at):
    """Save context information for the charm execution.

    Mostly to be used by builders.
    """
    os_platform = get_os_platform()

    # XXX Facundo 2021-03-29: the architectures list will be provided by the caller when
    # we integrate lifecycle lib in future branches
    architectures = [ARCH_TRANSLATIONS.get(os_platform.machine, os_platform.machine)]

    content = {
        'charmcraft-version': __version__,
        'charmcraft-started-at': started_at.isoformat() + "Z",
        'bases': [
            {
                'name': os_platform.system,
                'channel': os_platform.release,
                'architectures': architectures,
            }
        ],

    }
    filepath = basedir / 'manifest.yaml'
    if filepath.exists():
        raise CommandError(
            "Cannot write the manifest as there is already a 'manifest.yaml' in disk.")
    filepath.write_text(yaml.dump(content))
    return filepath
