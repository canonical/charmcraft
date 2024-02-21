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
"""New entrypoint for charmcraft."""
from __future__ import annotations

import pathlib
import shutil
import sys
from typing import Any, cast

import craft_cli
from craft_application import Application, AppMetadata, util
from craft_parts import plugins

from charmcraft import const, env, errors, models, services
from charmcraft.application import commands
from charmcraft.main import GENERAL_SUMMARY
from charmcraft.main import main as old_main
from charmcraft.parts import BundlePlugin, CharmPlugin, ReactivePlugin
from charmcraft.services import CharmcraftServiceFactory
from charmcraft.utils import humanize_list

APP_METADATA = AppMetadata(
    name="charmcraft",
    summary=GENERAL_SUMMARY,
    ProjectClass=models.CharmcraftProject,  # type: ignore[arg-type]
)


class Charmcraft(Application):
    """Charmcraft application definition."""

    def __init__(
        self,
        app: AppMetadata,
        services: CharmcraftServiceFactory,
    ) -> None:
        super().__init__(app=app, services=services)
        self._global_args: dict[str, Any] = {}
        self._dispatcher: craft_cli.Dispatcher | None = None

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        return self._command_groups

    def get_project(  # type: ignore[override]
        self, project_dir: pathlib.Path | None = None
    ) -> models.CharmcraftProject:
        """Get the charmcraft project."""
        if self.is_managed():
            project_dir = env.get_managed_environment_project_path()
        elif project_dir is None:
            project_dir = pathlib.Path(self._global_args.get("project_dir") or ".")
        return cast(models.CharmcraftProject, super().get_project(project_dir))

    def _project_vars(self, yaml_data: dict[str, Any]) -> dict[str, str]:
        """Return a dict with project-specific variables, for a craft_part.ProjectInfo."""
        return {"version": "unversioned"}

    def _extra_yaml_transform(
        self, yaml_data: dict[str, Any], *, build_on: str, build_for: str | None
    ) -> dict[str, Any]:
        yaml_data = yaml_data.copy()

        metadata_path = pathlib.Path(self._work_dir / "metadata.yaml")
        if metadata_path.exists():
            with metadata_path.open() as file:
                metadata_yaml = util.safe_yaml_load(file)
            if not isinstance(metadata_yaml, dict):
                raise errors.CraftError(
                    "Invalid file: 'metadata.yaml'",
                    resolution="Ensure metadata.yaml meets the juju metadata.yaml specification.",
                    docs_url="https://juju.is/docs/sdk/metadata-yaml",
                    retcode=65,  # Data error, per sysexits.h
                )
            duplicate_fields = []
            for field in const.METADATA_YAML_MIGRATE_FIELDS:
                if field in yaml_data and field in metadata_yaml:
                    duplicate_fields.append(field)
            if duplicate_fields:
                raise errors.CraftError(
                    "Fields in charmcraft.yaml cannot be duplicated in metadata.yaml",
                    details=f"Duplicate fields: {humanize_list(duplicate_fields, 'and')}",
                    resolution="Remove the duplicate fields from metadata.yaml.",
                    retcode=65,  # Data error. per sysexits.h
                )
            for field in const.METADATA_YAML_MIGRATE_FIELDS:
                yaml_data.setdefault(field, metadata_yaml.get(field))

        return yaml_data

    def _configure_services(self, platform: str | None, build_for: str | None) -> None:
        super()._configure_services(platform, build_for)
        self.services.set_kwargs(
            "package",
            project_dir=self._work_dir,
            platform=platform,
        )

    def configure(self, global_args: dict[str, Any]) -> None:
        """Configure the application using any global arguments."""
        super().configure(global_args)
        self._global_args = global_args
        if not self.services.ProviderClass.is_managed():
            # Do not do strict resolution here, as commands such as `init` will create
            # the project directory.
            project_dir = pathlib.Path(global_args.get("project_dir") or ".").resolve()
            self._work_dir = project_dir
        else:
            self._work_dir = env.get_managed_environment_project_path()

    @property
    def app_config(self) -> dict[str, Any]:
        """Charmcraft-specific application config to send to commands."""
        config = super().app_config
        config.setdefault("global_args", self._global_args)
        return config

    def _get_dispatcher(self) -> craft_cli.Dispatcher:
        """Get the dispatcher, with a charmcraft-specific side-effect of storing it on the app."""
        self._dispatcher = super()._get_dispatcher()
        return self._dispatcher

    def run_managed(self, platform: str | None, build_for: str | None) -> None:
        """Run charmcraft in managed mode.

        Overrides the craft-application managed mode runner to move packed files
        as needed.
        """
        dispatcher = self._dispatcher or self._get_dispatcher()
        command = dispatcher.load_command(self.app_config)

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
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})

    charmcraft_services = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)

    commands.fill_command_groups(app)

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
