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

import craft_providers
from craft_application import services
from craft_providers import bases

from charmcraft import env
from charmcraft.const import EXPERIMENTAL_EXTENSIONS_ENV_VAR


class ProviderService(services.ProviderService):
    """Business logic for getting providers."""

    def setup(self) -> None:
        """Set up the provider service for Charmcraft."""
        self.environment["CHARMCRAFT_MANAGED_MODE"] = "1"

        # Pass-through host environment that target may need.
        for env_key in ["http_proxy", "https_proxy", "no_proxy", EXPERIMENTAL_EXTENSIONS_ENV_VAR]:
            if env_key in os.environ:
                self.environment[env_key] = os.environ[env_key]

    def get_base(
        self,
        base_name: bases.BaseName | tuple[str, str],
        *,
        instance_name: str,
        **kwargs: bool | str | None | pathlib.Path,
    ) -> craft_providers.Base:
        """Get the base configuration from a base name.

        :param base_name: The base to lookup.
        :param instance_name: A name to assign to the instance.
        :param kwargs: Additional keyword arguments are sent directly to the base.

        If no cache_path is included, adds one.
        """
        # Forward the shared cache path.
        if "cache_path" not in kwargs:
            kwargs["cache_path"] = env.get_host_shared_cache_path()
        return super().get_base(
            base_name,
            instance_name=instance_name,
            # craft-application annotation is incorrect
            **kwargs,  # type: ignore[arg-type]
        )
