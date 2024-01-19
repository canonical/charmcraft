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

import contextlib
import os
import pathlib
from collections.abc import Generator

import craft_application
import craft_providers
from craft_application import models


class ProviderService(craft_application.ProviderService):
    """Business logic for getting providers."""

    def __init__(
        self,
        app: craft_application.AppMetadata,
        services: craft_application.ServiceFactory,
        *,
        project: models.Project,
        work_dir: pathlib.Path,
    ):
        super().__init__(app, services, project=project, work_dir=work_dir)
        self.output_dir = pathlib.Path.cwd()

    def setup(self) -> None:
        """Set up the provider service for Charmcraft."""
        self.environment["CHARMCRAFT_MANAGED_MODE"] = "1"

        # Pass-through host environment that target may need.
        for env_key in ["http_proxy", "https_proxy", "no_proxy"]:
            if env_key in os.environ:
                self.environment[env_key] = os.environ[env_key]

    @contextlib.contextmanager
    def instance(
        self,
        build_info: models.BuildInfo,
        *,
        work_dir: pathlib.Path,
        allow_unstable: bool = True,
        **kwargs: bool | str | None,
    ) -> Generator[craft_providers.Executor, None, None]:
        """Get an instance for charmcraft."""
        with super().instance(
            build_info, work_dir=work_dir, allow_unstable=allow_unstable, **kwargs
        ) as instance:
            # Mount the output directory in the instance so the package service can
            instance.mount(host_source=self.output_dir, target=pathlib.PurePath("/root/output"))

            yield instance
