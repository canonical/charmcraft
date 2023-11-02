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

"""Central configuration management.

Using pydantic's BaseModel, this module supports the translation of the
charmcraft.yaml to a python object.

Configuration Schema
====================

type: [string] one of "charm" or "bundle"

charmhub:
  api-url: [HttpUrl] optional, defaults to "https://api.charmhub.io"
  storage-url: [HttpUrl] optional, defaults to "https://storage.snapcraftcontent.com"
  registry-url = [HttpUrl] optional, defaults to "https://registry.jujucharms.com"

parts:
  charm:
    charm-entrypoint: [string] optional, defaults to "src/charm.py"
    charm-requirements: [list of strings] optional, defaults to ["requirements.txt"] if present
    prime: [list of strings]

  bundle:
    prime: [list of strings]

bases: [list of bases and/or long-form base configurations]

analysis:
  ignore:
    attributes: [list of attribute names to ignore]
    linting: [list of linter names to ignore]

actions:
  my-action:
    description: Action as defined at https://juju.is/docs/sdk/actions


Object Definitions
==================

Base
****

Object with the following properties:
- name: [string] name of base
- channel: [string] name of channel
- architectures: [list of strings], defaults to [<host-architecture>]

BaseConfiguration
*****************

Object with the following properties:
- build-on: [list of bases] to build on
- run-on: [list of bases] that build-on entries may run on

"""

import datetime
import pathlib

from charmcraft import const
from charmcraft.env import (
    get_managed_environment_project_path,
    is_charmcraft_running_in_managed_mode,
)
from charmcraft.models.charmcraft import CharmcraftConfig, Project
from charmcraft.utils import load_yaml


def load(dirpath: str | None) -> CharmcraftConfig:
    """Load the config from charmcraft.yaml in the indicated directory."""
    if dirpath is None:
        if is_charmcraft_running_in_managed_mode():
            dirpath = get_managed_environment_project_path()
        else:
            dirpath = pathlib.Path.cwd()
    else:
        dirpath = pathlib.Path(dirpath).expanduser().resolve()

    now = datetime.datetime.utcnow()

    content = load_yaml(dirpath / const.CHARMCRAFT_FILENAME)
    if content is None:
        # configuration is mandatory only for some commands; when not provided, it will
        # be initialized all with defaults (but marked as not provided for later verification)
        return CharmcraftConfig(
            type="charm",
            project=Project(
                dirpath=dirpath,
                config_provided=False,
                started_at=now,
            ),
            name="missing-charm-name",
            summary="missing-charm-summary",
            description="missing-charm-description",
        )

    return CharmcraftConfig.unmarshal(
        content,
        project=Project(
            dirpath=dirpath,
            config_provided=True,
            started_at=now,
        ),
    )
