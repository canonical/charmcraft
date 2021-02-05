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


def get_field_reference(path):
    """Get a field indicator from the received path."""
    if isinstance(path[-1], int):
        field = '.'.join(list(path)[:-1])
        ref = "item {} in '{}' field".format(path[-1], field)
    else:
        field = '.'.join(path)
        ref = "'{}' field".format(field)
    return ref


def adapt_validation_error(error):
    """Take a jsonschema.ValidationError and create a proper CommandError."""
    if error.validator == 'required':
        msg = "Bad charmcraft.yaml content; missing fields: {}.".format(
            ', '.join(error.validator_value))
    elif error.validator == 'type':
        expected_type = TYPE_TRANSLATOR.get(error.validator_value, error.validator_value)
        field_ref = get_field_reference(error.absolute_path)
        msg = "Bad charmcraft.yaml content; the {} must be a {}: got '{}'.".format(
            field_ref, expected_type, error.instance.__class__.__name__)
    elif error.validator == 'enum':
        field_ref = get_field_reference(error.absolute_path)
        msg = "Bad charmcraft.yaml content; the {} must be one of: {}.".format(
            field_ref, ', '.join(map(repr, error.validator_value)))
    elif error.validator == 'format':
        field_ref = get_field_reference(error.absolute_path)
        msg = "Bad charmcraft.yaml content; the {} {}: got {!r}.".format(
            field_ref, error.cause, error.instance)
    else:
        # safe fallback
        msg = error.message

    raise CommandError(msg)


@format_checker.checks('url', raises=ValueError)
def check_url(value):
    """Check that the URL has at least scheme and net location."""
    if isinstance(value, str):
        url = urlparse(value)
        if url.scheme and url.netloc:
            return True
    raise ValueError("must be a full URL (e.g. 'https://some.server.com')")


@format_checker.checks('relative_path', raises=ValueError)
def check_relative_paths(value):
    """Check that the received paths are all valid relative ones."""
    if isinstance(value, str):
        # check if it's an absolute path using POSIX's '/' (not os.path.sep, as the charm's
        # config is independent of the platform where charmcraft is running)
        if value and value[0] != '/':
            return True
    raise ValueError("must be a valid relative URL")


@attr.s(kw_only=True, frozen=True)
class CharmhubConfig:
    """Configuration for all Charmhub related options."""

    api_url = attr.ib(default='https://api.charmhub.io')
    storage_url = attr.ib(default='https://storage.snapcraftcontent.com')

    @classmethod
    def from_dict(cls, source):
        """Build from a raw dict."""
        return cls(**source)


class BasicPrime(tuple):
    """Hold the list of files to include, specified under parts/bundle/prime configs.

    This is a intermediate structure until we have the full Lifecycle in place.
    """

    @classmethod
    def from_dict(cls, parts):
        """Build from a dicts sequence."""
        prime = parts.get('bundle', {}).get('prime', [])
        return cls(prime)


@attr.s(kw_only=True, frozen=True)
class Project:
    """Configuration for all project-related options, used internally."""

    dirpath = attr.ib(default=None)
    config_provided = attr.ib(default=None)


@attr.s(kw_only=True, frozen=True)
class Config:
    """Root of all the configuration."""

    charmhub = attr.ib(default={}, converter=CharmhubConfig.from_dict)
    parts = attr.ib(default={}, converter=BasicPrime.from_dict)
    type = attr.ib(default=None)

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
            'additionalProperties': False,
        },
        'parts': {
            'type': 'object',
            'properties': {
                'bundle': {
                    'type': 'object',
                    'properties': {
                        'prime': {
                            'type': 'array',
                            'items': {
                                'type': 'string',
                                'format': 'relative_path',
                            },
                        },
                    },
                },
            },
        },
    },
    'required': ['type'],
    'additionalProperties': False,
}


def load(dirpath):
    """Load the config from charmcraft.yaml in the indicated directory."""
    if dirpath is None:
        dirpath = pathlib.Path.cwd()
    else:
        dirpath = pathlib.Path(dirpath).expanduser().resolve()

    content = load_yaml(dirpath / 'charmcraft.yaml')
    if content is None:
        # configuration is mandatory only for some commands; when not provided, it will
        # be initialized all with defaults (but marked as not provided for later verification)
        content = {}
        config_provided = False

    else:
        # config provided! validate the loaded config is ok and mark as such
        try:
            jsonschema.validate(
                instance=content, schema=CONFIG_SCHEMA, format_checker=format_checker)
        except jsonschema.ValidationError as exc:
            adapt_validation_error(exc)
        config_provided = True

    # inject project's config
    content['project'] = Project(dirpath=dirpath, config_provided=config_provided)

    return Config(**content)
