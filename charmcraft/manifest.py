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

"""Charmcraft manifest.yaml related functionality."""

import datetime
import logging
import pathlib
from typing import Optional

import yaml

from charmcraft import __version__, config
from charmcraft.cmdbase import CommandError

logger = logging.getLogger(__name__)


def create_manifest(
    basedir: pathlib.Path,
    started_at: datetime.datetime,
    bases_config: Optional[config.BasesConfiguration],
):
    """Create manifest.yaml in basedir for given base configuration.

    :param basedir: Directory to create Charm in.
    :param started_at: Build start time.
    :param bases_config: Relevant bases configuration, if any.

    :returns: Path to created manifest.yaml.
    """
    content = {
        "charmcraft-version": __version__,
        "charmcraft-started-at": started_at.isoformat() + "Z",
    }

    if bases_config is not None:
        bases = [
            {
                "name": r.name,
                "channel": r.channel,
                "architectures": r.architectures,
            }
            for r in bases_config.run_on
        ]
        content["bases"] = bases

    filepath = basedir / "manifest.yaml"
    if filepath.exists():
        raise CommandError(
            "Cannot write the manifest as there is already a 'manifest.yaml' in disk."
        )
    filepath.write_text(yaml.dump(content))
    return filepath
