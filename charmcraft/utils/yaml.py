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
"""YAML-related utilities for Charmcraft."""
from typing import Any

import yaml
from craft_cli import emit


def load_yaml(fpath) -> dict[str, Any] | None:
    """Return the content of a YAML file."""
    if not fpath.is_file():
        emit.debug(f"Couldn't find config file {str(fpath)!r}")
        return None
    try:
        with fpath.open("rb") as fh:
            content = yaml.safe_load(fh)
    except (yaml.error.YAMLError, OSError) as err:
        emit.debug(f"Failed to read/parse config file {str(fpath)!r}: {err!r}")
        return None
    return content
