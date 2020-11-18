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

from charmcraft.cmdbase import CommandError

from collections import UserDict


def load_yaml(fpath):  #FIXME: use the one from "utils"
    """Return the content of a YAML file."""
    import yaml
    if not fpath.exists():
        logger.debug("Couldn't find config file %s", fpath)
        return
    try:
        with fpath.open('rb') as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        logger.error("Failed to read/parse config file %s (got %r)", fpath, err)
        return
    return content


class _Config(UserDict):
    """Hold the config from charmcraft.yaml."""

    def __init__(self):
        self.data = {}

    def _validate(self, raw_data):
        """Validate the content loaded from charmcraft.yaml."""
        if not isinstance(raw_data, dict):
            raise CommandError("Invalid charmcraft.yaml structure: must be a dictionary.")

    def init(self, project_directory):
        """Init the config with the loaded charmcraft.yaml from project's directory."""
        if project_directory is None:
            project_directory = pathlib.Path.cwd()
        else:
            project_directory = pathlib.Path(project_directory)
            #FIXME: check if exists and it's a directory

        content = load_yaml(project_directory / 'charmcraft.yaml')
        self._validate(content)
        self.data = content


config = _Config()
