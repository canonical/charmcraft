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
from typing import Any

import craft_application
import craft_cli
from craft_application import util
from craft_parts.plugins import plugins
from overrides import override

from charmcraft import extensions, models, preprocess, services
from charmcraft.application import commands
from charmcraft.parts import BundlePlugin, CharmPlugin, ReactivePlugin
from charmcraft.services import CharmcraftServiceFactory

GENERAL_SUMMARY = """
Charmcraft helps build, package and publish operators on Charmhub.

Together with the Python Operator Framework, charmcraft simplifies
operator development and collaboration.

See https://charmhub.io/publishing for more information.
"""

APP_METADATA = craft_application.AppMetadata(
    name="charmcraft",
    summary=GENERAL_SUMMARY,
    ProjectClass=models.CharmcraftProject,
    BuildPlannerClass=models.CharmcraftBuildPlanner,
    source_ignore_patterns=["*.charm", "charmcraft.yaml"],
)

PRIME_BEHAVIOUR_CHANGE_MESSAGE = (
    "IMPORTANT: The behaviour of the 'prime' keyword has changed in Charmcraft 3. This "
    "keyword will no longer add files that would otherwise be excluded from the "
    "charm, instead filtering existing files. Additional files may be added using the "
    "'dump' plugin.\n"
    "To include extra files, see: https://juju.is/docs/sdk/include-extra-files-in-a-charm"
)


class Charmcraft(craft_application.Application):
    """Charmcraft application definition."""

    def __init__(
        self,
        app: craft_application.AppMetadata,
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
        # We only need to warn people once.
        if self.is_managed():
            return
        has_primed_part = False
        if "parts" in yaml_data:
            prime_changed_extensions = {"charm", "reactive", "bundle"}
            for name, part in yaml_data["parts"].items():
                if not {name, part.get("plugin", None)} & prime_changed_extensions:
                    continue
                if "prime" in part:
                    has_primed_part = True
        if has_primed_part:
            craft_cli.emit.progress(PRIME_BEHAVIOUR_CHANGE_MESSAGE, permanent=True)

    def _extra_yaml_transform(
        self, yaml_data: dict[str, Any], *, build_on: str, build_for: str | None
    ) -> dict[str, Any]:

        # Extensions get applied on as close as possible to what the user provided.
        yaml_data = extensions.apply_extensions(self.project_dir, yaml_data.copy())

        # Preprocessing "magic" to create a fully-formed charm.
        preprocess.add_default_parts(yaml_data)
        preprocess.add_bundle_snippet(self.project_dir, yaml_data)
        preprocess.add_config(self.project_dir, yaml_data)
        preprocess.add_actions(self.project_dir, yaml_data)
        preprocess.add_metadata(self.project_dir, yaml_data)

        self._check_deprecated(yaml_data)
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

    def _expand_environment(self, yaml_data: dict[str, Any], build_for: str) -> None:
        """Perform expansion of project environment variables.

        :param yaml_data: The project's yaml data.
        :param build_for: The architecture to build for.
        """
        if "-" in build_for:
            build_for = util.get_host_architecture()
            craft_cli.emit.debug(
                "Expanding environment variables with the host architecture "
                f"{build_for!r} as the build-for architecture because multiple "
                "run-on architectures were specified."
            )
        super()._expand_environment(yaml_data, build_for)


def main() -> int:
    """Run craft-application based charmcraft."""
    charmcraft_services = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)

    commands.fill_command_groups(app)

    return app.run()
