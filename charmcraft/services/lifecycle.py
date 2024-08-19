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

from craft_application import services, util
from craft_cli import emit
from overrides import override


class LifecycleService(services.LifecycleService):
    """Business logic for lifecycle builds."""

    def setup(self) -> None:
        """Do Charmcraft-specific setup work."""
        self._manager_kwargs.setdefault("project_name", self._project.name)
        super().setup()

    @override
    def _get_build_for(self) -> str:
        build_for = super()._get_build_for()
        if "-" not in build_for:
            if self._build_plan and self._build_plan[0].build_for == "all":
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
