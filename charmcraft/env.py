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

"""Charmcraft environment utilities."""


import distutils.util
import os
import sys

from charmcraft.cmdbase import CommandError


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


def is_charmcraft_running_in_supported_environment():
    """Check if Charmcraft is running in a supported environment."""
    return sys.platform == "linux" and is_charmcraft_running_from_snap()


def ensure_charmcraft_environment_is_supported():
    """Assert that environment is supported.

    :raises CommandError: if unsupported environment.
    """
    if (
        not is_charmcraft_running_in_supported_environment()
        and not is_charmcraft_running_in_developer_mode()
    ):
        raise CommandError(
            "For a supported user experience, please use the Charmcraft snap. "
            "For more information, please see https://snapcraft.io/charmcraft"
        )
