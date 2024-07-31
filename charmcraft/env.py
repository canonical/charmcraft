# Copyright 2021-2022 Canonical Ltd.
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

"""Charmcraft environment utilities."""
import dataclasses
import os
import pathlib

import platformdirs
from craft_application.util import strtobool

from charmcraft import const


def get_host_shared_cache_path() -> pathlib.Path:
    """Path for host shared cache."""
    shared_cache_env = os.getenv(const.SHARED_CACHE_ENV_VAR)
    if shared_cache_env is not None:
        cache_path = pathlib.Path(shared_cache_env).expanduser().resolve()
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    return platformdirs.user_cache_path(appname="charmcraft", ensure_exists=True)


def get_managed_environment_home_path() -> pathlib.Path:
    """Path for home when running in managed environment."""
    return pathlib.Path("/root")


def get_managed_environment_log_path() -> pathlib.Path:
    """Path for charmcraft log when running in managed environment."""
    return pathlib.Path("/tmp/charmcraft.log")


def get_charm_builder_metrics_path() -> pathlib.Path:
    """Path for charmcraft metrics when running charm_builder."""
    return pathlib.Path("/tmp/charm_builder_metrics.json")


def get_managed_environment_project_path() -> pathlib.Path:
    """Path for project when running in managed environment."""
    return get_managed_environment_home_path() / "project"


def is_charmcraft_running_from_snap() -> bool:
    """Check if charmcraft is running from the snap."""
    return os.getenv("SNAP_NAME") == "charmcraft" and os.getenv("SNAP") is not None


def is_charmcraft_running_in_managed_mode() -> bool:
    """Check if charmcraft is running in a managed environment."""
    managed_flag = os.getenv(const.MANAGED_MODE_ENV_VAR, os.getenv("CRAFT_MANAGED_MODE", "n"))
    return strtobool(managed_flag)


@dataclasses.dataclass(frozen=True)
class CharmhubConfig:
    """Definition of Charmhub endpoint configuration."""

    api_url: str = "https://api.charmhub.io"
    storage_url: str = "https://storage.snapcraftcontent.com"
    registry_url: str = "https://registry.jujucharms.com"


DEFAULT_CHARMHUB_CONFIG = CharmhubConfig()


def get_store_config() -> CharmhubConfig:
    """Get the appropriate configuration for the store."""
    api_url = os.getenv(const.STORE_API_ENV_VAR, DEFAULT_CHARMHUB_CONFIG.api_url)
    storage_url = os.getenv(const.STORE_STORAGE_ENV_VAR, DEFAULT_CHARMHUB_CONFIG.storage_url)
    registry_url = os.getenv(const.STORE_REGISTRY_ENV_VAR, DEFAULT_CHARMHUB_CONFIG.registry_url)
    return CharmhubConfig(api_url=api_url, storage_url=storage_url, registry_url=registry_url)
