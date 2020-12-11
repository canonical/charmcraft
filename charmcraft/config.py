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

"""Central configuration management."""

import pathlib
from urllib.parse import urlparse

import attr

from charmcraft.cmdbase import CommandError
from charmcraft.utils import load_yaml


def _get_key(config, field):
    """Get the complete path of the key in the config."""
    section = getattr(config, 'section', None)
    if section:
        key = '{}.{}'.format(section, field.name)
    else:
        key = field.name
    return key


def _check_type(config, field, value):
    """Check that the value is instance of the specified type."""
    if not isinstance(value, field.type):
        key = _get_key(config, field)
        raise CommandError(
            "Bad charmcraft.yaml content; field '{}' must be a {}: got {!r}."
            .format(key, field.type.__name__, value))


def _check_url(config, field, value):
    """Check that the URL has at least scheme and net location."""
    url = urlparse(value)
    if not url.scheme or not url.netloc:
        key = _get_key(config, field)
        raise CommandError(
            "Bad charmcraft.yaml content; field '{}' must be a full URL "
            "(e.g. 'https://some.server.com'): got {!r}.".format(key, value))


def _check_typefield(config, field, value):
    """Check that the value of 'type' field is valid."""
    # None is allowed until we make mandatory this configuration field
    if value not in ('charm', 'bundle', None):
        key = _get_key(config, field)
        raise CommandError(
            "Bad charmcraft.yaml content; field '{}' (if present) must value 'charm' or 'bundle': "
            "got {!r}.".format(key, value))


@attr.s(kw_only=True, frozen=True)
class _CharmhubConfig:
    section = 'charmhub'

    api_url = attr.ib(
        type=str, default='https://api.staging.charmhub.io',
        validator=[_check_url, _check_type])
    storage_url = attr.ib(
        type=str, default='https://storage.staging.snapcraftcontent.com',
        validator=[_check_url, _check_type])

    @classmethod
    def from_dict(cls, source=None):
        """Build from a raw dict."""
        if source is None:
            return cls()

        if not isinstance(source, dict):
            raise CommandError(
                "Bad charmcraft.yaml content; the 'charmhub' field must be a dict: got {!r}."
                .format(type(source).__name__))
        return cls(**source)


class _BasicPrime(tuple):
    """Hold the list of files to include, specified under parts/bundle/prime configs.

    This is a intermediate structure until we have the full Lifecycle in place.
    """
    @classmethod
    def from_dict(cls, parts):
        """Build from a dicts sequence."""
        if not isinstance(parts, dict):
            raise CommandError(
                "Bad charmcraft.yaml content; the 'parts' field must be a dict: got {!r}."
                .format(type(parts).__name__))

        bundle = parts.get('bundle', {})
        if not isinstance(bundle, dict):
            raise CommandError(
                "Bad charmcraft.yaml content; the 'parts.bundle' field must be a dict: got {!r}."
                .format(type(bundle).__name__))

        prime = bundle.get('prime', [])
        if not isinstance(prime, list):
            raise CommandError(
                "Bad charmcraft.yaml content; the 'parts.bundle.prime' field must be a list: "
                "got {!r}.".format(type(prime).__name__))

        # validate that all are relative
        for spec in prime:
            # check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
            # config is independent of the platform where charmcraft is running)
            if spec[0] == '/':
                raise CommandError(
                    "Bad charmcraft.yaml content; the paths specifications in "
                    "'parts.bundle.prime' must be relative: found {!r}.".format(spec))
        return cls(prime)


@attr.s(kw_only=True, frozen=True)
class Config:
    charmhub = attr.ib(default={}, converter=_CharmhubConfig.from_dict)
    parts = attr.ib(default={}, converter=_BasicPrime.from_dict)
    type = attr.ib(default=None, validator=[_check_typefield])

    # this value is provided by the code itself, not the user, as convenience for the
    # rest of the code
    project_dirpath = attr.ib(default=None)

    @classmethod
    def from_file(cls, project_directory):
        """Load the config from charmcraft.yaml in project's directory."""
        if project_directory is None:
            project_directory = pathlib.Path.cwd()
        else:
            project_directory = pathlib.Path(project_directory)

        content = load_yaml(project_directory / 'charmcraft.yaml')
        if content is None:
            content = {}
        elif not isinstance(content, dict):
            raise CommandError("Invalid charmcraft.yaml structure: must be a dictionary.")

        content['project_dirpath'] = project_directory
        return cls(**content)
