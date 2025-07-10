# Copyright 2025 Canonical Ltd.
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
"""Model for a Charmcraft Platforms entries."""

import pydantic
from craft_application.models.platforms import Platform


class CharmPlatform(Platform):
    @pydantic.field_validator("build_on", "build_for", mode="after")
    @classmethod
    def _validate_architectures(cls, values: list[str]) -> list[str]:
        return values

    @pydantic.field_validator("build_on", mode="after")
    @classmethod
    def _validate_build_on_real_arch(cls, values: list[str]) -> list[str]:
        return values
