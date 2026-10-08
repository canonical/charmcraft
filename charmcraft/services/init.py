# Copyright 2026 Canonical Ltd.
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

"""Charmcraft-specific project initialization."""

from __future__ import annotations

import os
import pathlib
import re
from datetime import date
from typing import TYPE_CHECKING, Any

import jinja2
from craft_application.services import InitService
from craft_cli import CraftError, emit
from typing_extensions import override

if TYPE_CHECKING:
    from craft_application.application import AppMetadata
    from craft_application.services import ServiceFactory

_CHARM_NAME_REGEX = re.compile(r"[a-z][a-z0-9-]*[a-z0-9]$")
_NOTABLE_PROJECT_FILES = {
    "charmcraft.yaml",
    "pyproject.toml",
    "README.md",
    "requirements.txt",
    "spread.yaml",
    "spread/deploy/basic/task.yaml",
    "src/charm.py",
}


def _get_users_full_name_gecos() -> str | None:
    """Get the user's full name from GECOS."""
    try:
        import pwd  # noqa: PLC0415
    except ImportError:
        return None
    try:
        return pwd.getpwuid(os.getuid()).pw_gecos.split(",", 1)[0]
    except KeyError:
        return None


def _make_workload_module_name(charm_name: str) -> str:
    """Derive the workload module name from the charm name."""
    module_name = charm_name.replace("-", "_")
    generic_names = [
        "k8s_charm",
        "k8s_operator",
        "machine_charm",
        "machine_operator",
        "vm_charm",
        "vm_operator",
        "charm",
        "operator",
        "k8s",
        "machine",
        "vm",
    ]
    if module_name in generic_names:
        return "workload"
    for generic_name in generic_names:
        generic_suffix = f"_{generic_name}"
        if module_name.endswith(generic_suffix):
            return module_name[: -len(generic_suffix)]
    return module_name


def _make_success_message(project_files: list[str]) -> str:
    """Create Charmcraft's project summary."""
    project_files_str = "\n".join(sorted(project_files, key=str.casefold))
    default_message = f"""\
Created project files for your charm:

{project_files_str}
...
"""
    uv_message = """\
To manage your charm's dependencies, use uv.

To migrate from the Charm plugin to the uv plugin, see:
https://canonical.com/juju/docs/charmcraft/stable/howto/migrate-plugins/charm-to-uv/

Next steps:

1. Run 'uv lock'
2. Edit charmcraft.yaml and pyproject.toml to provide metadata, then commit (including uv.lock)
3. Write your charm code and tests
"""
    if "pyproject.toml" in project_files and "requirements.txt" not in project_files:
        return f"{default_message}\n{uv_message}"
    return default_message


class CharmcraftInitService(InitService):
    """Initialize Charmcraft projects using generic init infrastructure."""

    def __init__(
        self,
        app: AppMetadata,
        services: ServiceFactory,
    ) -> None:
        super().__init__(app, services)
        self._author: str | None = None
        self._force = False
        self._workload_module = "workload"

    def configure_init(
        self,
        *,
        author: str | None,
        force: bool,
        project_name: str,
    ) -> None:
        """Configure values supplied by the init command."""
        self._author = author
        self._force = force
        self._workload_module = _make_workload_module_name(project_name)

    @override
    def validate_project_name(self, name: str, *, use_default: bool = False) -> str:
        """Validate a charm name without falling back to a generated name."""
        if not isinstance(name, str) or not _CHARM_NAME_REGEX.match(name):
            raise CraftError(
                f"{name} is not a valid charm name. "
                "The name must start with a lowercase letter "
                "and contain only alphanumeric characters and hyphens."
            )
        return name

    @override
    def check_for_existing_files(
        self,
        *,
        project_dir: pathlib.Path,
        template_dir: pathlib.Path,
    ) -> None:
        """Check for output collisions unless force mode is enabled."""
        if not self._force:
            super().check_for_existing_files(
                project_dir=project_dir,
                template_dir=template_dir,
            )

    @override
    def _get_template_files(self, template_dir: pathlib.Path) -> list[str]:
        """Map the generic workload template to its generated module name."""
        template_files = super()._get_template_files(template_dir)
        workload_template = "src/workload.py"
        if workload_template in template_files:
            template_files.remove(workload_template)
            template_files.append(f"src/{self._workload_module}.py")
        return template_files

    @override
    def _get_context(self, name: str, *, project_dir: pathlib.Path) -> dict[str, Any]:
        """Add Charmcraft template values to the generic context."""
        author = self._author
        if author is None:
            author = _get_users_full_name_gecos()
        if not author:
            raise CraftError(
                "Unable to automatically determine author's name, specify it with --author"
            )

        context = super()._get_context(name, project_dir=project_dir)
        context.update(
            author=author,
            year=date.today().year,
            class_name="".join(re.split(r"\W+", name.title())) + "Charm",
            workload_module=self._workload_module,
        )
        return context

    @override
    def _render_project(
        self,
        environment: jinja2.Environment,
        project_dir: pathlib.Path,
        template_dir: pathlib.Path,
        context: dict[str, Any],
    ) -> None:
        """Render a project, rename its workload module, and summarize it."""
        existing_files = (
            {
                path.relative_to(project_dir)
                for path in project_dir.rglob("*")
                if path.is_file()
            }
            if project_dir.exists()
            else set()
        )
        workload_path = project_dir / "src/workload.py"
        workload_existed = workload_path.exists()

        super()._render_project(environment, project_dir, template_dir, context)

        if not workload_existed and workload_path.exists():
            destination = workload_path.with_name(f"{self._workload_module}.py")
            if destination != workload_path:
                if destination.exists():
                    workload_path.unlink()
                else:
                    workload_path.rename(destination)

        created_files = {
            path.relative_to(project_dir)
            for path in project_dir.rglob("*")
            if path.is_file()
        } - existing_files
        notable_files = [
            path.as_posix()
            for path in created_files
            if path.as_posix() in _NOTABLE_PROJECT_FILES
            or path.as_posix() == f"src/{self._workload_module}.py"
        ]
        for line in _make_success_message(notable_files).splitlines():
            emit.message(line)
