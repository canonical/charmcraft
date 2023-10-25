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
import pathlib
import signal
import sys
from typing import Any, cast

import craft_application
import craft_cli
import craft_parts
import craft_providers
from craft_application import Application, AppMetadata
from craft_parts import plugins

from charmcraft import errors, models, services
from charmcraft.application import commands
from charmcraft.application.commands.base import CharmcraftCommand
from charmcraft.main import GENERAL_SUMMARY
from charmcraft.main import main as old_main
from charmcraft.parts import BundlePlugin, CharmPlugin, ReactivePlugin
from charmcraft.services import CharmcraftServiceFactory

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

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        lifecycle_commands = commands.get_lifecycle_command_group()
        other_commands = craft_application.application.commands.get_other_command_group()

        merged: dict[str, list[type[craft_cli.BaseCommand]]] = {}
        all_groups = [
            lifecycle_commands,
            other_commands,
            *self._command_groups,
        ]

        # Merge the default command groups with those provided by the application,
        # so that we don't get multiple groups with the same name.
        for group in all_groups:
            merged.setdefault(group.name, []).extend(group.commands)

        return [craft_cli.CommandGroup(name, commands_) for name, commands_ in merged.items()]

    def _project_vars(self, yaml_data: dict[str, Any]) -> dict[str, str]:
        """Return a dict with project-specific variables, for a craft_part.ProjectInfo."""
        return {"version": "unversioned"}

    def _configure_services(self, platform: str | None, build_for: str | None) -> None:
        self.services.set_kwargs(
            "lifecycle",
            cache_dir=self.cache_dir,
            work_dir=self._work_dir,
            build_for=build_for,
        )
        self.services.set_kwargs(
            "provider",
            work_dir=self._work_dir,
        )
        self.services.set_kwargs(
            "package",
            project_dir=self._work_dir,
            platform=platform,
        )
        self.services.set_kwargs("analysis", project_dir=self._work_dir)

    def configure(self, global_args: dict[str, Any]) -> None:
        """Configure the application using any global arguments."""
        super().configure(global_args)
        self._global_args = global_args
        if not self.services.ProviderClass.is_managed():
            project_dir = pathlib.Path(global_args.get("project_dir") or ".").resolve(strict=True)
            self._work_dir = project_dir

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

    def run(self) -> int:  # (too many branches due to error handling)
        """Bootstrap and run the application."""
        dispatcher = self._get_dispatcher()
        craft_cli.emit.trace("Preparing application...")

        return_code = 1  # General error
        try:
            command = cast(
                CharmcraftCommand,
                dispatcher.load_command(
                    {"app": self.app, "services": self.services, "global_args": self._global_args}
                ),
            )
            platform = getattr(dispatcher.parsed_args, "platform", None)
            build_for = getattr(dispatcher.parsed_args, "build_for", None)
            self._configure_services(platform, build_for)

            if not command.run_managed(dispatcher.parsed_args()):
                # command runs in the outer instance
                craft_cli.emit.debug(f"Running {self.app.name} {command.name} on host")
                if command.always_load_project:
                    self.services.project = self.project
                return_code = dispatcher.run() or 0
            elif not self.services.ProviderClass.is_managed():
                # command runs in inner instance, but this is the outer instance
                self.services.project = self.project
                self.run_managed(platform, build_for)
                return_code = 0
            else:
                # command runs in inner instance
                self.services.project = self.project
                return_code = dispatcher.run() or 0
        except craft_cli.ArgumentParsingError as err:
            print(err, file=sys.stderr)  # to stderr, as argparse normally does
            craft_cli.emit.ended_ok()
            return_code = 64  # Command line usage error from sysexits.h
        except KeyboardInterrupt as err:
            self._emit_error(craft_cli.CraftError("Interrupted."), cause=err)
            return_code = 128 + signal.SIGINT
        except craft_cli.CraftError as err:
            self._emit_error(err)
        except craft_parts.PartsError as err:
            self._emit_error(
                craft_cli.CraftError(err.brief, details=err.details, resolution=err.resolution)
            )
            return_code = 1
        except craft_providers.ProviderError as err:
            self._emit_error(
                craft_cli.CraftError(err.brief, details=err.details, resolution=err.resolution)
            )
            return_code = 1
        except Exception as err:  # pylint: disable=broad-except
            self._emit_error(craft_cli.CraftError(f"{self.app.name} internal error: {err!r}"))
            if os.getenv("CRAFT_DEBUG") == "1":
                raise
            return_code = 70  # EX_SOFTWARE from sysexits.h
        else:
            craft_cli.emit.ended_ok()

        return return_code


def main() -> int:
    """Run craft-application based charmcraft with classic fallback."""
    plugins.register({"charm": CharmPlugin, "bundle": BundlePlugin, "reactive": ReactivePlugin})

    charmcraft_services = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=charmcraft_services)

    app.add_global_argument(
        craft_cli.GlobalArgument(
            "project_dir",
            "option",
            "-p",
            "--project-dir",
            "Specify the project's directory (defaults to current)",
        )
    )

    app.add_command_group("Basic", [commands.InitCommand])
    app.add_command_group(
        "Store",
        [
            # auth
            commands.LoginCommand,
            commands.LogoutCommand,
            commands.WhoamiCommand,
            # name handling
            commands.RegisterCharmNameCommand,
            commands.RegisterBundleNameCommand,
            commands.UnregisterNameCommand,
            commands.ListNamesCommand,
            # pushing files and checking revisions
            commands.UploadCommand,
            commands.ListRevisionsCommand,
            # release process, and show status
            commands.ReleaseCommand,
            commands.PromoteBundleCommand,
            commands.StatusCommand,
            commands.CloseCommand,
            # libraries support
            commands.CreateLibCommand,
            commands.PublishLibCommand,
            commands.ListLibCommand,
            commands.FetchLibCommand,
            # resources support
            commands.ListResourcesCommand,
            commands.ListResourceRevisionsCommand,
            commands.UploadResourceCommand,
        ],
    )

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
