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

from craft_application import ServiceFactory

# Add new services to this mapping to add them to the service factory
# Internal service name : Stringified service class name
_SERVICES: dict[str, str] = {
    "analysis": "AnalysisService",
    "build_plan": "CharmBuildPlanService",
    "charm_libs": "CharmLibsService",
    "image": "ImageService",
    "lifecycle": "LifecycleService",
    "package": "PackageService",
    "project": "ProjectService",
    "provider": "ProviderService",
    "remote_build": "RemoteBuildService",
    "store": "StoreService",
}


def register_services() -> None:
    """Register Charmcraft-specific services."""
    for name, service in _SERVICES.items():
        module_name = name.replace("_", "")
        ServiceFactory.register(
            name, service, module=f"charmcraft.services.{module_name}"
        )
