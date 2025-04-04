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

from craft_application.services.service_factory import ServiceFactory


def register_services():
    """Register charmcraft's services with the service factory."""
    ServiceFactory.register(
        "analysis", "AnalysisService", module="charmcraft.services.analysis"
    )
    ServiceFactory.register(
        "charm_libs", "CharmLibsService", module="charmcraft.services.charmlibs"
    )
    ServiceFactory.register("image", "ImageService", module="charmcraft.services.image")
    ServiceFactory.register(
        "lifecycle", "LifecycleService", module="charmcraft.services.lifecycle"
    )
    ServiceFactory.register(
        "package", "PackageService", module="charmcraft.services.package"
    )
    ServiceFactory.register(
        "provider", "ProviderService", module="charmcraft.services.provider"
    )
    ServiceFactory.register(
        "remote_build", "RemoteBuildService", module="charmcraft.services.remotebuild"
    )
    ServiceFactory.register("store", "StoreService", module="charmcraft.services.store")
