# Copyright 2020-2022 Canonical Ltd.
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

import datetime
import enum
import functools
import itertools
import os
import pathlib
import platform
import sys
import zipfile
from pathlib import Path
from collections import namedtuple, defaultdict
from dataclasses import dataclass
from stat import S_IRGRP, S_IROTH, S_IRUSR, S_IXGRP, S_IXOTH, S_IXUSR
from typing import Any, Dict, Optional, Iterable, Container, Union

import yaml
from craft_cli import emit, CraftError
from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined

from charmcraft.env import is_charmcraft_running_in_managed_mode
from charmcraft.errors import DuplicateCharmsError, InvalidCharmPathError

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
    "AMD64": "amd64",  # Windows support
}

PathOrString = Union[os.PathLike, str]


@functools.total_ordering
@enum.unique
class Risk(enum.Enum):
    """Standard risk tracks for a channel, orderable but not comparable to an int."""

    STABLE = 0
    CANDIDATE = 1
    BETA = 2
    EDGE = 3

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        return NotImplemented


@dataclass(frozen=True)
class ChannelData:
    """Data class for a craft store channel."""

    track: Optional[str]
    risk: Risk
    branch: Optional[str]

    @classmethod
    def from_str(cls, name: str):
        """Parse a channel name from a string using the standard store semantics.

        https://snapcraft.io/docs/channels
        """
        invalid_channel_error = CraftError(f"Invalid channel name: {name!r}")
        parts = name.split("/")
        if len(parts) == 1:
            try:
                risk = Risk[parts[0].upper()]
            except KeyError:
                raise invalid_channel_error from None
            else:
                parts = [None, risk, None]
        elif len(parts) == 2:
            try:
                risk = Risk[parts[0].upper()]
                parts.insert(0, None)
            except KeyError:
                try:
                    risk = Risk[parts[1].upper()]
                    parts.append(None)
                except KeyError:
                    raise invalid_channel_error from None
        elif len(parts) == 3:
            try:
                risk = Risk[parts[1].upper()]
            except KeyError:
                raise invalid_channel_error from None
        else:
            raise invalid_channel_error
        return cls(parts[0], risk, parts[2])

    @property
    def name(self) -> str:
        """Get the channel name as a string."""
        risk = self.risk.name.lower()
        return "/".join(i for i in (self.track, risk, self.branch) if i is not None)


def make_executable(fh):
    """Make open file fh executable."""
    fileno = fh.fileno()
    mode = os.fstat(fileno).st_mode
    mode_r = mode & S_IRALL
    mode_x = mode_r >> 2
    mode = mode | mode_x
    os.fchmod(fileno, mode)


def load_yaml(fpath: Path) -> Optional[Dict[str, Any]]:
    """Return the content of a YAML file."""
    if not fpath.is_file():
        emit.debug(f"Couldn't find config file {str(fpath)!r}")
        return
    try:
        with fpath.open("rb") as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        emit.debug(f"Failed to read/parse config file {str(fpath)!r}: {err!r}")
        return
    return content


def get_templates_environment(templates_dir):
    """Create and return a Jinja environment to deal with the templates."""
    templates_dir = os.path.join("templates", templates_dir)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as PyInstaller bundle. For more information:
        # https://pyinstaller.readthedocs.io/en/stable/runtime-information.html
        # In this scenario we need to load from the data location that is unpacked
        # into the temporary directory at runtime (sys._MEIPASS).
        emit.debug(f"Bundle directory: {sys._MEIPASS}")
        loader = FileSystemLoader(os.path.join(sys._MEIPASS, templates_dir))
    else:
        loader = PackageLoader("charmcraft", templates_dir)

    env = Environment(
        loader=loader,
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
                if revision >= 0:
                    return ResourceOption(name, revision)
        msg = (
            "the resource format must be <name>:<revision> (revision being a non-negative integer)"
        )
        raise ValueError(msg)


def useful_filepath(filepath):
    """Return a valid Path with user name expansion for filepath.

    CraftError is raised if filepath is not a valid file or is not readable.
    """
    filepath = pathlib.Path(filepath).expanduser()
    if not os.access(filepath, os.R_OK):
        raise CraftError("Cannot access {!r}.".format(str(filepath)))
    if not filepath.is_file():
        raise CraftError("{!r} is not a file.".format(str(filepath)))
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
            emit.debug("Unable to locate 'os-release' file, using default values")
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

    :returns: True if answer starts with [yY], False if answer starts with [nN],
        otherwise the default.
    """
    if is_charmcraft_running_in_managed_mode():
        raise RuntimeError("confirmation not yet supported in managed-mode")

    if not sys.stdin.isatty():
        return default

    choices = " [Y/n]: " if default else " [y/N]: "

    with emit.pause():
        reply = input(prompt + choices).lower().strip()

    if reply and reply[0] == "y":
        return True
    elif reply and reply[0] == "n":
        return False
    else:
        return default


def format_timestamp(dt: datetime.datetime) -> str:
    """Convert a datetime object (with or without timezone) to a string.

    The format is

        <DATE>T<TIME>Z

    Always in UTC.
    """
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(None) is not None:
        # timezone aware
        dtz = dt.astimezone(datetime.timezone.utc)
    else:
        # timezone naive, assume it's UTC
        dtz = dt
    return dtz.strftime("%Y-%m-%dT%H:%M:%SZ")


def humanize_list(items: Iterable[str], conjunction: str) -> str:
    """Format a list into a human-readable string.

    :param items: list to humanize, must not be empty
    :param conjunction: the conjunction used to join the final element to
                        the rest of the list (e.g. 'and').
    """
    if not items:
        raise ValueError("Cannot humanize an empty list.")
    *initials, final = map(repr, sorted(items))
    if not initials:
        return final
    return f"{', '.join(initials)} {conjunction} {final}"


def build_zip(zip_path: PathOrString, prime_dir: PathOrString) -> None:
    """Build the final file."""
    zip_path = pathlib.Path(zip_path).resolve()
    prime_dir = pathlib.Path(prime_dir).resolve()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as file:
        for file_path in prime_dir.rglob("*"):
            if not file_path.is_file():
                continue
            file.write(file_path, file_path.relative_to(prime_dir))


def find_charm_sources(
    base_path: pathlib.Path, charm_names: Container[str]
) -> Dict[str, pathlib.Path]:
    """Find all charm directories matching the given names under a base path.

    :param base_path: The base directory under which to look.
    :param charm_names: A container with charm names to find.
    :returns: A dictionary mapping charm names to their paths.
    :raises: DuplicateCharmsError if a charm is found in multiple directories.
    """
    duplicate_charms = defaultdict(list)
    charm_paths = {}
    potential_paths = itertools.chain(
        (p.parent.resolve() for p in base_path.glob("charms/*/metadata.yaml")),
        (p.parent.resolve() for p in base_path.glob("operators/*/metadata.yaml")),
        (p.parent.resolve() for p in base_path.glob("*/metadata.yaml")),
    )
    potential_paths = filter(lambda p: (p / "charmcraft.yaml").exists(), potential_paths)
    for path in potential_paths:
        if path in charm_paths.values():  # Symlinks can cause ignorable duplicate paths.
            continue
        try:
            charm_name = get_charm_name_from_path(path)
        except InvalidCharmPathError:
            continue
        if charm_name not in charm_names:  # We only care if the charm is listed for finding
            continue
        if charm_name != path.name:
            emit.verbose(f"Charm {charm_name!r} found in non-matching path {path}")
            continue
        if charm_name in charm_paths:
            duplicate_charms[charm_name].append(path)
        else:
            charm_paths[charm_name] = path
    if duplicate_charms:
        raise DuplicateCharmsError(duplicate_charms)
    return charm_paths


def get_charm_name_from_path(path: pathlib.Path) -> str:
    """Get a charm's name from a given path.

    :param path: The path to investigate.
    :returns: The name of the charm in this path
    :raises: InvalidCharmPathError if the path given is not a valid charm source.
    """
    charmcraft_yaml = load_yaml(path / "charmcraft.yaml")
    if charmcraft_yaml is None or charmcraft_yaml.get("type") != "charm":
        raise InvalidCharmPathError(path)
    metadata_yaml = load_yaml(path / "metadata.yaml")
    if metadata_yaml is None or "name" not in metadata_yaml:
        raise InvalidCharmPathError(path)
    return metadata_yaml["name"]
