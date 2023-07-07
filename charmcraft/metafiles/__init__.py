# Copyright 2023 Canonical Ltd.
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

"""Submodule for handling the all extra yaml files."""

import pathlib
from typing import Any, Dict

import yaml

from craft_cli import emit

__all__ = ["actions", "manifest", "metadata", "config", "read_yaml"]


def read_yaml(yaml_file_path: pathlib.Path) -> Dict[str, Any]:
    """Parse yaml file.

    :returns: the YAML decoded yaml content
    """
    emit.debug(f"Reading {str(yaml_file_path)!r}")
    with yaml_file_path.open("rt", encoding="utf8") as fh:
        return yaml.safe_load(fh)
