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
    """Validate that the value is instance of the specified type."""
    if not isinstance(value, field.type):
        key = _get_key(config, field)
        raise CommandError(
            "The config value {} must be a {}: got {!r}".format(key, field.type.__name__, value))


def _check_url(config, field, value):
    """Validate that the URL has at least scheme and net location."""
    url = urlparse(value)
    if not url.scheme or not url.netloc:
        key = _get_key(config, field)
        raise CommandError(
            "The config value {} must be a full URL (e.g. 'https://some.server.com'): got {!r}"
            .format(key, value))


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
    def from_dict(cls, source):
        """Build from a raw dict."""
        if not isinstance(source, dict):
            raise CommandError(
                "Bad charmcraft.yaml content: the 'charmhub' field must be a dict: got {!r}."
                .format(type(source).__name__))
        return cls(**source)


@attr.s(kw_only=True, frozen=True)
class Config:
    charmhub = attr.ib(default={}, converter=_CharmhubConfig.from_dict)

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

        return cls(**content)
