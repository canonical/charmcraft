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

"""Charmcraft project handle actions.yaml file."""

import pathlib
import logging
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def create_actions(
    basedir: pathlib.Path,
    actions: Optional[Dict[str, Any]] = None,
) -> Optional[pathlib.Path]:
    """Create actions.yaml in basedir for given project configuration.

    :param basedir: Directory to create Charm in.
    :param actions: Relevant bases configuration, if any.

    :returns: Path to created actions.yaml.
    """
    if actions is None:
        return None

    filepath = basedir / "actions.yaml"
    filepath.write_text(yaml.dump(actions))
    return filepath
