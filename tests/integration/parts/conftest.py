# Copyright 2024 Canonical Ltd.
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

import sys

import craft_platforms
import distro
import pytest
from craft_application import models
from craft_providers import bases

pytestmark = [
    pytest.mark.skipif(sys.platform != "linux", reason="craft-parts is linux-only")
]


@pytest.fixture
def build_plan() -> list[models.BuildInfo]:
    arch = craft_platforms.DebianArchitecture.from_host().value
    return [
        models.BuildInfo(
            base=bases.BaseName(distro.id(), distro.version()),
            build_on=arch,
            build_for="arm64",
            platform="distro-1-test64",
        )
    ]
