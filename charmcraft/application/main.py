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

import functools
import pathlib
import signal
import sys
from typing import Any

import craft_application
import craft_cli
from craft_application import Application, AppMetadata, ServiceFactory
from craft_application.services import service_factory
from craft_cli import emit
from craft_parts.plugins import plugins

from charmcraft import errors, models
from charmcraft.main import GENERAL_SUMMARY, PROJECT_DIR_ARGUMENT
from charmcraft.main import main as old_main
from charmcraft.parts import BundlePlugin, CharmPlugin
from charmcraft.reactive_plugin import ReactivePlugin
from charmcraft.services import (
    CharmcraftLifecycleService,
    CharmcraftPackageService,
    CharmcraftProviderService,
)

APP_METADATA = AppMetadata(
    name="charmcraft",
    summary=GENERAL_SUMMARY,
    ProjectClass=models.CharmcraftProject,
    source_ignore_patterns=[
        "*.charm",
        "*.zip",
    ],
)


class Charmcraft(Application):
    """Charmcraft application definition."""

    project_dir: pathlib.Path

    def __init__(self, app: AppMetadata, services: service_factory.ServiceFactory):
        super().__init__(app, services)
        self.add_global_argument(PROJECT_DIR_ARGUMENT)

    def _configure_services(
        self,
        platform: str | None,  # (Unused method argument)
        build_for: str | None,
    ) -> None:
        super()._configure_services(platform, build_for)
        self.services.set_kwargs("package", project_dir=self.project_dir)

    def configure(self, global_args: dict[str, Any]) -> None:
        self.project_dir = pathlib.Path(global_args["project_dir"] or ".").resolve()

    @functools.cached_property
    def project(self) -> models.CharmcraftProject:
        project_file = self.project_dir / f"{self.app.name}.yaml"
        craft_cli.emit.debug(f"Loading project file '{project_file!s}'")
        return self.app.ProjectClass.from_yaml_file(project_file)

    def _get_dispatcher(self) -> craft_cli.Dispatcher:
        """Configure charmcraft, including a fallback to the classic entrypoint.

        :side-effect: This method may exit the process.
        :raises: ClassicFallback: if the classic entry point should be used instead.

        :returns: A ready-to-run Dispatcher object
        """
        craft_cli.emit.init(
            mode=craft_cli.EmitterMode.BRIEF,
            appname=self.app.name,
            greeting=f"Starting {self.app.name}",
            log_filepath=self.log_path,
        )

        dispatcher = craft_application.application._Dispatcher(
            self.app.name,
            self.command_groups,
            summary=str(self.app.summary),
            extra_global_args=self._global_arguments,
        )

        try:
            craft_cli.emit.trace("pre-parsing arguments...")
            if "--version" in sys.argv or "-V" in sys.argv:
                raise errors.ClassicFallback
            else:
                global_args = dispatcher.pre_parse_args(sys.argv[1:])
        except KeyboardInterrupt as err:
            self._emit_error(craft_cli.CraftError("Interrupted."), cause=err)
            sys.exit(128 + signal.SIGINT)
        except (craft_cli.ProvideHelpException, craft_cli.ArgumentParsingError) as err:
            emit.debug(
                "Command not available through craft-application yet. "
                f"Falling back to classic: {err!r}"
            )
            raise errors.ClassicFallback
        craft_cli.emit.trace("Preparing application...")
        self.configure(global_args)

        return dispatcher


def main() -> int:
    """Run craft-application based charmcraft with classic fallback."""
    services = ServiceFactory(  # type: ignore[call-arg]
        app=APP_METADATA,
        LifecycleClass=CharmcraftLifecycleService,
        PackageClass=CharmcraftPackageService,
        ProviderClass=CharmcraftProviderService,
    )

    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})

    app = Charmcraft(
        app=APP_METADATA,
        services=services,
    )

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
