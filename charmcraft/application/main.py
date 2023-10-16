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

import os
import signal
import sys

import craft_cli
from craft_application import Application, AppMetadata
from craft_parts import plugins

from charmcraft import errors, models, services
from charmcraft.application.commands.lifecycle import get_lifecycle_command_group
from charmcraft.main import GENERAL_SUMMARY
from charmcraft.main import main as old_main
from charmcraft.parts import BundlePlugin, CharmPlugin
from charmcraft.reactive_plugin import ReactivePlugin

APP_METADATA = AppMetadata(
    name="charmcraft",
    summary=GENERAL_SUMMARY,
    ProjectClass=models.CharmcraftProject,  # type: ignore[arg-type]
)


class Charmcraft(Application):
    """Charmcraft application definition."""

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        lifecycle_commands = get_lifecycle_command_group()

        merged: dict[str, list[type[craft_cli.BaseCommand]]] = {}
        all_groups = [
            lifecycle_commands,
            # other_commands,
            *self._command_groups,
        ]

        # Merge the default command groups with those provided by the application,
        # so that we don't get multiple groups with the same name.
        for group in all_groups:
            merged.setdefault(group.name, []).extend(group.commands)

        return [craft_cli.CommandGroup(name, commands_) for name, commands_ in merged.items()]

    def _configure_services(self, platform: str | None, build_for: str | None) -> None:
        super()._configure_services(platform, build_for)
        self.services.set_kwargs(
            "package",
            work_dir=self._work_dir,
            prime_dir=self.services.lifecycle.prime_dir,
            platform=platform,
        )

    def _get_dispatcher(self) -> craft_cli.Dispatcher:  # type: ignore[override]
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
            streaming_brief=True,
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
                raise errors.ClassicFallback  # noqa: TRY301 (This is temporary)
            else:
                global_args = dispatcher.pre_parse_args(sys.argv[1:])
        except KeyboardInterrupt as err:
            self._emit_error(craft_cli.CraftError("Interrupted."), cause=err)
            sys.exit(128 + signal.SIGINT)
        except craft_cli.ProvideHelpException as err:
            print(err, file=sys.stderr)  # to stderr, as argparse normally does
            craft_cli.emit.ended_ok()
            sys.exit(0)
        except craft_cli.ArgumentParsingError as err:
            print(err, file=sys.stderr)  # to stderr, as argparse normally does
            craft_cli.emit.ended_ok()
            sys.exit(64)  # Command line usage error from sysexits.h
        except Exception as err:
            self._emit_error(
                craft_cli.CraftError(f"Internal error while loading {self.app.name}: {err!r}")
            )
            if os.getenv("CRAFT_DEBUG") == "1":
                raise
            sys.exit(70)  # EX_SOFTWARE from sysexits.h
        craft_cli.emit.trace("Preparing application...")
        self.configure(global_args)

        return dispatcher


def main() -> int:
    """Run craft-application based charmcraft with classic fallback."""
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})

    charmcraft_services = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
