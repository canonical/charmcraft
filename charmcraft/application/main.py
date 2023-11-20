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

import craft_cli
import craft_parts
import craft_providers
from craft_application import Application, AppMetadata, util
from craft_parts import plugins

from charmcraft import const, env, errors, models, services
from charmcraft.application import commands
from charmcraft.application.commands.base import CharmcraftCommand
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

    @property
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        return self._command_groups

    def _project_vars(self, yaml_data: dict[str, Any]) -> dict[str, str]:
        """Return a dict with project-specific variables, for a craft_part.ProjectInfo."""
        return {"version": "unversioned"}

    def _extra_yaml_transform(self, yaml_data: dict[str, Any]) -> dict[str, Any]:
        yaml_data = yaml_data.copy()

        metadata_path = pathlib.Path(self._work_dir / "metadata.yaml")
        if metadata_path.exists():
            with metadata_path.open() as file:
                metadata_yaml = util.safe_yaml_load(file)
            if not isinstance(metadata_yaml, dict):
                raise errors.CraftError(
                    "Invalid file: 'metadata.yaml'",
                    resolution="Ensure metadata.yaml is valid.",
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

    commands.fill_command_groups(app)

    try:
        return app.run()
    except errors.ClassicFallback:
        return old_main(sys.argv)
