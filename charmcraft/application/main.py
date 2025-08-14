# Copyright 2023-2025 Canonical Ltd.
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

import datetime
import pathlib
from typing import Any

import craft_application
import craft_cli
from craft_application import util
from craft_parts.plugins.plugins import PluginType
from overrides import override

from charmcraft import models, parts, services
from charmcraft.application import commands

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
    source_ignore_patterns=["*.charm", "charmcraft.yaml"],
    docs_url="https://documentation.ubuntu.com/charmcraft/{version}",
    supports_multi_base=True,
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
        services: craft_application.ServiceFactory,
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
            prime_changed_extensions = {"charm", "reactive"}
            for name, part in yaml_data["parts"].items():
                if not {name, part.get("plugin", None)} & prime_changed_extensions:
                    continue
                if "prime" in part:
                    has_primed_part = True
        if has_primed_part:
            craft_cli.emit.progress(PRIME_BEHAVIOUR_CHANGE_MESSAGE, permanent=True)

    def _configure_services(self, provider_name: str | None) -> None:
        self.services.update_kwargs(
            "project",
            project_dir=self.project_dir,
        )
        super()._configure_services(provider_name)
        self.services.update_kwargs(
            "charm_libs",
            project_dir=self.project_dir,
        )

    def configure(self, global_args: dict[str, Any]) -> None:
        """Configure the application using any global arguments."""
        super().configure(global_args)
        self._global_args = global_args
        if not util.is_managed_mode():
            self.services.get("state").set(
                "charmcraft",
                "started_at",
                value=datetime.datetime.now().isoformat(),
                overwrite=True,
            )

    def _get_dispatcher(self) -> craft_cli.Dispatcher:
        """Get the dispatcher, with a charmcraft-specific side-effect of storing it on the app."""
        self._dispatcher = super()._get_dispatcher()
        return self._dispatcher

    @override
    def _get_app_plugins(self) -> dict[str, PluginType]:
        return parts.get_app_plugins()

    @override
    def _pre_run(self, dispatcher: craft_cli.Dispatcher) -> None:
        """Override to get project_dir early."""
        super()._pre_run(dispatcher)
        if not self.is_managed() and not getattr(
            dispatcher.parsed_args(), "project_dir", None
        ):
            self.project_dir = pathlib.Path().expanduser().resolve()


def create_app() -> Charmcraft:
    """Create the Charmcraft application with its commands."""
    services.register_services()
    charmcraft_services = services.ServiceFactory(app=APP_METADATA)
    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)
    commands.fill_command_groups(app)

    return app


def get_app_info() -> tuple[craft_cli.Dispatcher, dict[str, Any]]:
    """Retrieve application info. Used by craft-cli's completion module."""
    app = create_app()
    dispatcher = app._create_dispatcher()

    return dispatcher, app.app_config


def main() -> int:
    """Run craft-application based charmcraft."""
    app = create_app()

    return app.run()
