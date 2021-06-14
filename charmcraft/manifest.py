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

from charmcraft import __version__, config, utils
from charmcraft.cmdbase import CommandError

logger = logging.getLogger(__name__)


def create_manifest(
    basedir: pathlib.Path,
    started_at: datetime.datetime,
    bases_config: Optional[config.BasesConfiguration] = None,
):
    """Create manifest.yaml in basedir for given base configuration.

    :param basedir: Directory to create Charm in.
    :param started_at: Build start time.
    :param bases_config: Relevant bases configuration.

    :returns: Path to created manifest.yaml.
    """
    if bases_config is None:
        os_platform = utils.get_os_platform()

        # XXX Facundo 2021-03-29: the architectures list will be provided by the caller when
        # we integrate lifecycle lib in future branches
        architectures = [utils.get_host_architecture()]

        # XXX Facundo 2021-04-19: these are temporary translations until charmcraft
        # changes to be a "classic" snap
        name_translation = {"ubuntu-core": "ubuntu"}
        channel_translation = {"20": "20.04"}
        name = os_platform.system.lower()
        name = name_translation.get(name, name)
        channel = channel_translation.get(os_platform.release, os_platform.release)
        bases = [
            {
                "name": name,
                "channel": channel,
                "architectures": architectures,
            }
        ]
    else:
        bases = [r.dict() for r in bases_config.run_on]

    content = {
        "charmcraft-version": __version__,
        "charmcraft-started-at": started_at.isoformat() + "Z",
        "bases": bases,
    }
    filepath = basedir / "manifest.yaml"
    if filepath.exists():
        raise CommandError(
            "Cannot write the manifest as there is already a 'manifest.yaml' in disk."
        )
    filepath.write_text(yaml.dump(content))
    return filepath
