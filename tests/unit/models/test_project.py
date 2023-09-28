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
"""Tests for Charmcraft project-related models."""
from typing import List

from charmcraft.models import project, charmcraft


# region CharmBuildInfo tests
def test_build_info_from_build_on_run_on(
    build_on_base: charmcraft.Base,
    build_on_arch: str,
    run_on: List[charmcraft.Base],
):
    info = project.CharmBuildInfo.from_build_on_run_on(
        build_on_base, build_on_arch, run_on, bases_index=10, build_on_index=256
    )


# endregion
