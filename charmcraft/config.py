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
import jsonschema

from charmcraft.cmdbase import CommandError
from charmcraft.utils import load_yaml

format_checker = jsonschema.FormatChecker()

# translator between "json" and pythonic yaml names
TYPE_TRANSLATOR = {
    'object': 'dict',
    'array': 'list',
}


def adapt_validation_error(error):
    """Take a jsonschema.ValidationError and create a proper CommandError."""
    field_path = '.'.join(error.absolute_path)
    if error.validator == 'required':
        msg = "Bad charmcraft.yaml content; missing fields: {}.".format(
            ', '.join(error.validator_value))
    elif error.validator == 'type':
        expected_type = TYPE_TRANSLATOR.get(error.validator_value, error.validator_value)
        msg = "Bad charmcraft.yaml content; the '{}' field must be a {}: got '{}'.".format(
            field_path, expected_type, error.instance.__class__.__name__)
    elif error.validator == 'enum':
        msg = "Bad charmcraft.yaml content; the '{}' field must be one of: {}.".format(
            field_path, ', '.join(map(repr, error.validator_value)))
    elif error.validator == 'format':
        msg = "Bad charmcraft.yaml content; the '{}' field {}: got {!r}.".format(
            field_path, error.cause, error.instance)
    else:
        # safe fallback
        msg = error.message

    raise CommandError(msg)


@format_checker.checks('url', raises=ValueError)
def _check_url(value):
    """Check that the URL has at least scheme and net location."""
    if isinstance(value, str):
        url = urlparse(value)
        if url.scheme and url.netloc:
            return True
    raise ValueError("must be a full URL (e.g. 'https://some.server.com')")


@attr.s(kw_only=True, frozen=True)
class _CharmhubConfig:
    """Configuration for all Charmhub related options."""
    api_url = attr.ib(default='https://api.staging.charmhub.io')
    storage_url = attr.ib(default='https://storage.staging.snapcraftcontent.com')

    @classmethod
    def from_dict(cls, source):
        """Build from a raw dict."""
        return cls(**source)


class _BasicPrime(tuple):
    """Hold the list of files to include, specified under parts/bundle/prime configs.

    This is a intermediate structure until we have the full Lifecycle in place.
    """
    @classmethod
    def from_dict(cls, parts):
        """Build from a dicts sequence."""
        prime = parts.get('bundle', {}).get('prime', [])

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
class _Project:
    """Configuration for all project-related options, used internally."""
    dirpath = attr.ib(default=None)


@attr.s(kw_only=True, frozen=True)
class _Config:
    """Root of all the configuration."""
    charmhub = attr.ib(default={}, converter=_CharmhubConfig.from_dict)
    parts = attr.ib(default={}, converter=_BasicPrime.from_dict)
    type = attr.ib()

    # this item is provided by the code itself, not the user, as convenience for the
    # rest of the code
    project = attr.ib(default=None)


CONFIG_SCHEMA = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string', 'enum': ['charm', 'bundle']},
        'charmhub': {
            'type': 'object',
            'properties': {
                'api_url': {'type': 'string', 'format': 'url'},
                'storage_url': {'type': 'string', 'format': 'url'},
            },
        },
        'parts': {
            'type': 'object',
            'properties': {
                'bundle': {
                    'type': 'object',
                    'properties': {
                        'prime': {'type': 'array'},
                    },
                },
            },
        },
    },
    'required': ['type'],
}


def load(dirpath):
    """Load the config from charmcraft.yaml in the indicated directory."""
    if dirpath is None:
        dirpath = pathlib.Path.cwd()
    else:
        dirpath = pathlib.Path(dirpath)

    content = load_yaml(dirpath / 'charmcraft.yaml')
    # XXX Facundo 2021-01-04: we will make this configuration mandatory in the future, but
    # so far is ok to not have it
    if content is None:
        return

    # validate the loaded config is ok
    try:
        jsonschema.validate(instance=content, schema=CONFIG_SCHEMA, format_checker=format_checker)
    except jsonschema.ValidationError as exc:
        adapt_validation_error(exc)

    # inject project's config
    content['project'] = _Project(dirpath=dirpath)

    return _Config(**content)
