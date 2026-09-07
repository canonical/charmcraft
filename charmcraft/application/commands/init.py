# Copyright 2020-2026 Canonical Ltd.
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

"""Infrastructure for the 'init' command."""

from __future__ import annotations

import argparse
import importlib.resources
import pathlib
from typing import cast

from craft_application.commands import InitCommand as BaseInitCommand
from craft_cli import CraftError

from charmcraft.services.init import CharmcraftInitService

DEFAULT_PROFILE = "kubernetes"
DEFAULT_BASES = {
    "django-framework": "ubuntu@24.04",
    "expressjs-framework": "ubuntu@24.04",
    "fastapi-framework": "ubuntu@24.04",
    "flask-framework": "ubuntu@24.04",
    "go-framework": "ubuntu@24.04",
    "kubernetes": "ubuntu@24.04",
    "machine": "ubuntu@24.04",
    "spring-boot-framework": "ubuntu@24.04",
}

_overview = """
Initialize a charm operator package tree and files.

This command creates a charm project in the current directory or in
<project-dir> when provided.

Available profiles are:
    kubernetes:
        A basic Kubernetes charm with example container.

    machine:
        A basic charm but meant to be deployed in machine-based environments,
        without container requirements.

    django-framework:
        A basic Kubernetes charm for a 12-factor Django app.

    expressjs-framework:
        A basic Kubernetes charm for a 12-factor ExpressJS app.

    fastapi-framework:
        A basic Kubernetes charm for a 12-factor FastAPI app.

    flask-framework:
        A basic Kubernetes charm for a 12-factor Flask app.

    go-framework:
        A basic Kubernetes charm for a 12-factor Go app.

    spring-boot-framework:
        A basic Kubernetes charm for a 12-factor Spring Boot app.

Use --base to select a base-specific variant of a profile when one is
available.
"""


class InitCommand(BaseInitCommand):
    """Initialize a directory to be a charm project."""

    help_msg = "Initialize a charm operator package tree and files"
    overview = _overview
    default_profile = DEFAULT_PROFILE

    @property
    def parent_template_dir(self) -> pathlib.Path:
        """Return the directory containing Charmcraft init profiles."""
        with importlib.resources.path(
            self._app.name, "templates"
        ) as parent_template_dir:
            return parent_template_dir / "init"

    @property
    def profiles(self) -> list[str]:
        """Return profile names without their base variant suffixes."""
        return sorted(
            {
                template_dir.name.partition("__")[0]
                for template_dir in self.parent_template_dir.iterdir()
                if template_dir.is_dir()
            }
        )

    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        """Specify Charmcraft's init parameters."""
        super().fill_parser(parser)
        parser.add_argument(
            "--author",
            help="The charm author; defaults to the current user name per GECOS",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Initialize without overwriting files that already exist",
        )
        parser.add_argument(
            "-p",
            "--project-dir",
            dest="project_dir_option",
            type=pathlib.Path,
            default=None,
            help="Deprecated alias for the positional <project-dir> argument",
        )

    def run(self, parsed_args: argparse.Namespace) -> None:
        """Initialize a charm project with Charmcraft-specific context."""
        project_dir = self._get_project_dir(parsed_args)
        if parsed_args.name is None:
            parsed_args.name = project_dir.name

        init_service = cast(CharmcraftInitService, self._services.get("init"))
        init_service.validate_project_name(parsed_args.name)
        init_service.configure_init(
            author=parsed_args.author,
            force=parsed_args.force,
            project_name=parsed_args.name,
        )
        super().run(parsed_args)

    def _get_template_dir(self, parsed_args: argparse.Namespace) -> pathlib.Path:
        """Resolve Charmcraft's default base before generic variant selection."""
        if parsed_args.base is None and parsed_args.profile in DEFAULT_BASES:
            return (
                self.parent_template_dir
                / f"{parsed_args.profile}__{DEFAULT_BASES[parsed_args.profile]}"
            )
        return super()._get_template_dir(parsed_args)

    @staticmethod
    def _get_project_dir(parsed_args: argparse.Namespace) -> pathlib.Path:
        """Resolve the positional project directory or its deprecated alias."""
        project_dir = parsed_args.project_dir
        project_dir_option = getattr(parsed_args, "project_dir_option", None)
        if project_dir is not None and project_dir_option is not None:
            raise CraftError(
                "Cannot use <project-dir> and --project-dir at the same time."
            )
        return pathlib.Path(
            project_dir or project_dir_option or pathlib.Path.cwd()
        ).resolve()
