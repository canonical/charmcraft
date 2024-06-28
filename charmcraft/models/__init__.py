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

"""Charmcraft pydantic models."""

from . import actions, config, metadata
from .charmcraft import Base
from .lint import CheckResult, CheckType, LintResult, ResultLevel
from .manifest import Attribute, Manifest
from .metadata import BundleMetadata, CharmMetadata, CharmMetadataLegacy
from .project import (
    CharmBuildInfo,
    CharmcraftBuildPlanner,
    CharmLib,
    CharmcraftProject,
    BasesCharm,
    PlatformCharm,
    Charm,
    Bundle,
)

__all__ = [
    "actions",
    "config",
    "metadata",
    "Base",
    "CheckResult",
    "CheckType",
    "LintResult",
    "ResultLevel",
    "Attribute",
    "Manifest",
    "Bundle",
    "BasesCharm",
    "PlatformCharm",
    "Charm",
    "CharmBuildInfo",
    "CharmcraftBuildPlanner",
    "CharmcraftProject",
    "CharmLib",
    "BundleMetadata",
    "CharmMetadata",
    "CharmMetadataLegacy",
]
