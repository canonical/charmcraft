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
from charmcraft.utils import load_yaml

from collections import UserDict


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

        content = load_yaml(project_directory / 'charmcraft.yaml')
        if content is None:
            # so far charmcraft.yaml is optional
            return

        self._validate(content)
        self.data = content


config = _Config()
