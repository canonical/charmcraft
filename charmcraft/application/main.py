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
"""New entrypoint for charmcraft."""
from __future__ import annotations

import pathlib
import shutil
import sys
from typing import Any

import craft_cli
from craft_application import Application, AppMetadata
from craft_parts.plugins import plugins
from overrides import override

from charmcraft import errors, extensions, models, preprocess, services
from charmcraft.application import commands
from charmcraft.main import GENERAL_SUMMARY
from charmcraft.main import main as old_main
from charmcraft.parts import BundlePlugin, CharmPlugin, ReactivePlugin
from charmcraft.services import CharmcraftServiceFactory

APP_METADATA = AppMetadata(
    name="charmcraft",
    summary=GENERAL_SUMMARY,
    ProjectClass=models.CharmcraftProject,
    BuildPlannerClass=models.CharmcraftBuildPlanner,
    source_ignore_patterns=["*.charm", "charmcraft.yaml"],
)


class Charmcraft(Application):
    """Charmcraft application definition."""

    def __init__(
        self,
        app: AppMetadata,
        services: CharmcraftServiceFactory,
    ) -> None:
        super().__init__(app=app, services=services, extra_loggers={"charmcraft"})
        self._global_args: dict[str, Any] = {}
        self._dispatcher: craft_cli.Dispatcher | None = None
        self._cli_loggers |= {"charmcraft"}

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        return self._command_groups

    def _project_vars(self, yaml_data: dict[str, Any]) -> dict[str, str]:
        """Return a dict with project-specific variables, for a craft_part.ProjectInfo."""
        return {"version": "unversioned"}

    def _check_deprecated(self, yaml_data: dict[str, Any]) -> None:
        """Check for deprecated fields in the yaml_data."""
        if "parts" in yaml_data:
            for k, v in yaml_data["parts"].items():
                if (k in ("charm", "reactive", "bundle")) or (
                    v.get("plugin", None) in ("charm", "reactive", "bundle")
                ):
                    if "prime" in v:
                        craft_cli.emit.progress(
                            "Warning: use of 'prime' in a charm part "
                            "is deprecated and no longer works, "
                            "see https://juju.is/docs/sdk/include-extra-files-in-a-charm",
                            permanent=True,
                        )

    def _extra_yaml_transform(
        self, yaml_data: dict[str, Any], *, build_on: str, build_for: str | None
    ) -> dict[str, Any]:
        self._check_deprecated(yaml_data)

        # Extensions get applied on as close as possible to what the user provided.
        yaml_data = extensions.apply_extensions(self.project_dir, yaml_data.copy())

        # Preprocessing "magic" to create a fully-formed charm.
        preprocess.add_default_parts(yaml_data)
        preprocess.add_bundle_snippet(self.project_dir, yaml_data)
        preprocess.add_config(self.project_dir, yaml_data)
        preprocess.add_actions(self.project_dir, yaml_data)
        preprocess.add_metadata(self.project_dir, yaml_data)

        return yaml_data

    def _configure_services(self, provider_name: str | None) -> None:
        super()._configure_services(provider_name)
        self.services.set_kwargs(
            "package",
            project_dir=self.project_dir,
            build_plan=self._build_plan,
        )

    def configure(self, global_args: dict[str, Any]) -> None:
        """Configure the application using any global arguments."""
        super().configure(global_args)
        self._global_args = global_args

    def _get_dispatcher(self) -> craft_cli.Dispatcher:
        """Get the dispatcher, with a charmcraft-specific side-effect of storing it on the app."""
        self._dispatcher = super()._get_dispatcher()
        return self._dispatcher

    @override
    def _get_app_plugins(self) -> dict[str, plugins.PluginType]:
        return {"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin}

    @override
    def _pre_run(self, dispatcher: craft_cli.Dispatcher) -> None:
        """Override to get project_dir early."""
        super()._pre_run(dispatcher)
        if not self.is_managed() and not getattr(dispatcher.parsed_args(), "project_dir", None):
            self.project_dir = pathlib.Path().expanduser().resolve()

    def run_managed(self, platform: str | None, build_for: str | None) -> None:
        """Run charmcraft in managed mode.

        Overrides the craft-application managed mode runner to move packed files
        as needed.
        """
        dispatcher = self._dispatcher or self._get_dispatcher()
        command = dispatcher.load_command(self.app_config)
        self._work_dir = self.project_dir

        super().run_managed(platform, build_for)

        if not self.is_managed() and isinstance(command, commands.PackCommand):
            if output_dir := getattr(dispatcher.parsed_args(), "output", None):
                output_path = pathlib.Path(output_dir).resolve()
                output_path.mkdir(parents=True, exist_ok=True)
                package_file_path = self._work_dir / ".charmcraft_output_packages.txt"
                if package_file_path.exists():
                    package_files = package_file_path.read_text().splitlines(keepends=False)
                    package_file_path.unlink(missing_ok=True)
                    for filename in package_files:
                        shutil.move(str(self._work_dir / filename), output_path / filename)


def main() -> int:
    """Run craft-application based charmcraft with classic fallback."""
    charmcraft_services = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)

    commands.fill_command_groups(app)

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
