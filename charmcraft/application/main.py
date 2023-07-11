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

import signal
import sys

import craft_cli
from craft_application import Application, AppMetadata, ServiceFactory
from craft_cli import emit

import charmcraft.main
from charmcraft import errors, models

APP_METADATA = AppMetadata(
    name="charmcraft",
    summary=charmcraft.main.GENERAL_SUMMARY,
    ProjectClass=models.charmcraft.Project,
)


class Charmcraft(Application):
    """Charmcraft application definition."""

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Excluding lifecycle commands for right now."""
        return self._command_groups

    def _configure_services(self) -> None:
        super()._configure_services()
        self.services.set_kwargs(
            "package",
            work_dir=self._work_dir,
            prime_dir=self.services.lifecycle.prime_dir,
        )

    def _get_dispatcher(self) -> craft_cli.Dispatcher:
        """Configure charmcraft, including a fallback to the classic entrypoint.

        Side-effect: This method may exit the process.
        Raises: ClassicFallback() to fall back to the classic interface.

        :returns: A ready-to-run Dispatcher object
        """
        craft_cli.emit.init(
            mode=craft_cli.EmitterMode.BRIEF,
            appname=self.app.name,
            greeting=f"Starting {self.app.name}",
            log_filepath=self.log_path,
        )

        dispatcher = craft_cli.Dispatcher(
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
        app=APP_METADATA, PackageClass=None  # SourcePackageService,
    )

    app = Charmcraft(app=APP_METADATA, services=services)

    try:
        return app.run()
    except errors.ClassicFallback:
        return charmcraft.main.main(sys.argv)