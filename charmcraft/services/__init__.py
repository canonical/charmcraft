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
from charmcraft.services.remotebuild import RemoteBuildService

from craft_application import ServiceFactory

from .analysis import AnalysisService
from .image import ImageService
from .lifecycle import LifecycleService
from .package import PackageService
from .provider import ProviderService
from .store import StoreService
from .. import models


@dataclasses.dataclass
class CharmcraftServiceFactory(ServiceFactory):
    """Factory class for lazy-loading Charmcraft services."""

    PackageClass: type[PackageService] = PackageService
    LifecycleClass: type[LifecycleService] = LifecycleService
    ProviderClass: type[ProviderService] = ProviderService
    AnalysisClass: type[AnalysisService] = AnalysisService
    StoreClass: type[StoreService] = StoreService
    RemoteBuildClass: type[RemoteBuildService] = RemoteBuildService
    ImageClass: type[ImageService] = ImageService

    if TYPE_CHECKING:
        # Cheeky hack that lets static type checkers report the correct types.
        # Any apps that add their own services should do this too.
        analysis: AnalysisService = None  # type: ignore[assignment]
        image: ImageService = None  # type: ignore[assignment]
        lifecycle: LifecycleService = None  # type: ignore[assignment]
        package: PackageService = None  # type: ignore[assignment]
        project: models.CharmcraftProject = None  # type: ignore[assignment]
        provider: ProviderService = None  # type: ignore[assignment]
        store: StoreService = None  # type: ignore[assignment]


__all__ = [
    "AnalysisService",
    "ImageService",
    "LifecycleService",
    "PackageService",
    "ProviderService",
    "CharmcraftServiceFactory",
]
