# Copyright 2021 Canonical Ltd.
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

"""Logic for snap configuration."""

from dataclasses import dataclass

import snaphelpers


@dataclass
class CharmcraftSnapConfiguration:
    """Charmcraft's snap configuration options."""

    provider: str | None = None


def _get_config_key(*, snap_config: snaphelpers.SnapConfig, key: str, default=None):
    """Get snap configuration for specified key.

    :returns: Returns key's value or default if undefined.
    """
    try:
        return snap_config.get(key)
    except snaphelpers.UnknownConfigKey:
        return default


def get_snap_configuration() -> CharmcraftSnapConfiguration:
    """Get unvalidated snap configuration.

    :returns: Current snap configuration.
    """
    snap_config = snaphelpers.SnapConfig()
    provider = _get_config_key(snap_config=snap_config, key="provider")

    return CharmcraftSnapConfiguration(provider=provider)


def validate_snap_configuration(cfg: CharmcraftSnapConfiguration):
    """Validate given snap configuration.

    :raises ValueError: on error.
    """
    if cfg.provider is not None and cfg.provider not in ["lxd", "multipass"]:
        raise ValueError(f"provider {cfg.provider!r} is not supported")
