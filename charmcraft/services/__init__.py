# Copyright 2023-2024 Canonical Ltd.
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
"""Service classes charmcraft."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from craft_application import ServiceFactory


def register_services():
    """Register the services to use in Charmcraft."""
    ServiceFactory.register(
        "analysis",
        "AnalysisService",
        module="charmcraft.services.analysis",
    )
    ServiceFactory.register(
        "build_plan",
        "CharmBuildPlanService",
        module="charmcraft.services.buildplan",
    )
    ServiceFactory.register(
        "charm_libs",
        "CharmLibsService",
        module="charmcraft.services.charmlibs",
    )
    ServiceFactory.register(
        "image",
        "ImageService",
        module="charmcraft.services.image",
    )
    ServiceFactory.register(
        "lifecycle",
        "LifecycleService",
        module="charmcraft.services.lifecycle",
    )
    ServiceFactory.register(
        "package",
        "PackageService",
        module="charmcraft.services.package",
    )
    ServiceFactory.register(
        "project", "ProjectService", module="charmcraft.services.project"
    )
    ServiceFactory.register(
        "provider",
        "ProviderService",
        module="charmcraft.services.provider",
    )
    ServiceFactory.register(
        "remote_build",
        "RemoteBuildService",
        module="charmcraft.services.remotebuild",
    )
    ServiceFactory.register(
        "store",
        "StoreService",
        module="charmcraft.services.store",
    )
