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
"""Service class for running craft lifecycle commands."""
from __future__ import annotations

import os
import pathlib

from craft_application import services

from charmcraft import const


class LifecycleService(services.LifecycleService):
    """Business logic for lifecycle builds."""

    def setup(self) -> None:
        """Do Charmcraft-specific setup work."""
        self._manager_kwargs.setdefault("project_name", self._project.name)
        self._manager_kwargs.setdefault("parallel_build_count", os.cpu_count())
        if not self._services.ProviderClass.is_managed():
            self._work_dir = pathlib.Path(self._work_dir, const.BUILD_DIRNAME)
            self._work_dir.mkdir(exist_ok=True)
        super().setup()
