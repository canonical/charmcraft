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


import distutils.util
import os
import pathlib
from typing import Optional

import platformdirs

from charmcraft.const import SHARED_CACHE_ENV_VAR


def get_host_shared_cache_path():
    """Path for host shared cache."""
    shared_cache_env = os.getenv(SHARED_CACHE_ENV_VAR)
    if shared_cache_env is not None:
        cache_path = pathlib.Path(shared_cache_env).expanduser().resolve()
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    return platformdirs.user_cache_path(appname="charmcraft", ensure_exists=True)


def get_managed_environment_home_path():
    """Path for home when running in managed environment."""
    return pathlib.Path("/root")


def get_managed_environment_log_path():
    """Path for charmcraft log when running in managed environment."""
    return pathlib.Path("/tmp/charmcraft.log")


def get_managed_environment_metrics_path():
    """Path for charmcraft metrics when running in managed environment."""
    return pathlib.Path("/tmp/metrics.json")


def get_charm_builder_metrics_path():
    """Path for charmcraft metrics when running charm_builder."""
    return pathlib.Path("/tmp/charm_builder_metrics.json")


def get_managed_environment_project_path():
    """Path for project when running in managed environment."""
    return get_managed_environment_home_path() / "project"


def get_managed_environment_snap_channel() -> Optional[str]:
    """User-specified channel to use when installing Charmcraft snap from Snap Store.

    :returns: Channel string if specified, else None.
    """
    return os.getenv("CHARMCRAFT_INSTALL_SNAP_CHANNEL")


def is_charmcraft_running_from_snap():
    """Check if charmcraft is running from the snap."""
    return os.getenv("SNAP_NAME") == "charmcraft" and os.getenv("SNAP") is not None


def is_charmcraft_running_in_developer_mode():
    """Check if Charmcraft is running under developer mode."""
    developer_flag = os.getenv("CHARMCRAFT_DEVELOPER", "n")
    return distutils.util.strtobool(developer_flag) == 1


def is_charmcraft_running_in_managed_mode():
    """Check if charmcraft is running in a managed environment."""
    managed_flag = os.getenv("CHARMCRAFT_MANAGED_MODE", "n")
    return distutils.util.strtobool(managed_flag) == 1
