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

"""Service class for creating providers."""
from __future__ import annotations

import os
import pathlib

from craft_application import services, AppMetadata, ServiceFactory

from charmcraft import models, providers


class ProviderService(services.ProviderService):
    """Business logic for getting providers."""

    def setup(self) -> None:
        """Set up the provider service for Charmcraft"""
        self.environment["CHARMCRAFT_MANAGED_MODE"] = "1"

        # Pass-through host environment that target may need.
        for env_key in ["http_proxy", "https_proxy", "no_proxy"]:
            if env_key in os.environ:
                self.environment[env_key] = os.environ[env_key]


