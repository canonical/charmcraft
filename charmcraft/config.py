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

from charmcraft.commands import CommandError

from collections import UserDict


class _Config(UserDict):
    """Hold the config from charmcraft.yaml."""

    def __init__(self):
        self.data = {}

    def _validate(self, raw_data):
        """Validate the content loaded from charmcraft.yaml."""
        if not isinstance(raw_data, dict):
            raise CommandError("Invalid charmcraft.yaml structure: must be a dictionary.")

    def init(self, raw_data):
        """Init the config with the loaded charmcraft.yaml file content."""
        self._validate(raw_data)
        self.data = raw_data


config = _Config()
