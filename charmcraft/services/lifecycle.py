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

from typing import cast

import craft_parts
from craft_application import services, util
from craft_cli import emit
from overrides import override

from charmcraft import dispatch


class LifecycleService(services.LifecycleService):
    """Business logic for lifecycle builds."""

    @override
    def setup(self) -> None:
        self._manager_kwargs["project_name"] = self._services.get("project").get().name
        super().setup()

    @override
    def _get_build_for(self) -> str:
        build_for = super()._get_build_for()
        if "-" not in build_for:
            build_plan = self._services.get("build_plan").plan()
            if build_plan and build_plan[0].build_for == "all":
                emit.progress(
                    "WARNING: Charmcraft does not validate that charms with "
                    "architecture 'all' are fully architecture agnostic.",
                    permanent=True,
                )
            return build_for

        # Multi-arch builds: Tell craft-parts that we're building for any foreign
        # architecture (to trick it into trying to cross-compile anything, leading
        # to more likely failures.)
        emit.progress(
            "WARNING: Charmcraft does not validate that charms with multiple "
            "given architectures are architecture agnostic.",
            permanent=True,
        )
        host_arch = util.get_host_architecture()
        for arch in build_for.split("-"):
            if arch != host_arch:
                return arch

        return host_arch

    @override
    def post_prime(self, step_info: craft_parts.StepInfo) -> bool:
        return_value = super().post_prime(step_info)

        project_info = cast(craft_parts.ProjectInfo, step_info.project_info)
        # TODO: include an entrypoint override. #1896
        return return_value | dispatch.create_dispatch(
            prime_dir=project_info.dirs.prime_dir
        )
