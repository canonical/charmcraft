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

"""Service class for packing."""
from __future__ import annotations

import pathlib
import shutil
from typing import TYPE_CHECKING, Optional, cast

import craft_application
import yaml
from craft_application import services
from craft_cli import emit

from charmcraft import models, utils
from charmcraft.models.manifest import Manifest
from charmcraft.models.metadata import BundleMetadata, CharmMetadata
from charmcraft.models.project import Bundle, Charm, CharmcraftProject

if TYPE_CHECKING:
    from charmcraft.services import CharmcraftServiceFactory
else:
    CharmcraftServiceFactory = "CharmcraftServiceFactory"


class PackageService(services.PackageService):
    """Business logic for creating packages."""

    _project: models.CharmcraftProject  # type: ignore[assignment]
    _services: CharmcraftServiceFactory

    def __init__(
        self,
        app: craft_application.AppMetadata,
        project: CharmcraftProject,
        services: CharmcraftServiceFactory,
        *,
        project_dir: pathlib.Path,
        platform: str | None,
    ) -> None:
        super().__init__(app, services, project=cast(craft_application.models.Project, project))
        self.project_dir = project_dir.resolve(strict=True)
        self._platform = platform

    def pack(self, prime_dir: pathlib.Path, dest: pathlib.Path) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param prime_dir: Directory path to the prime directory.
        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        if self._project.type == "charm":
            return [self.pack_charm(prime_dir, dest)]
        if self._project.type == "bundle":
            raise NotImplementedError("Bundle packing not done yet (CRAFT-2144)")
        raise NotImplementedError("No general packing available yet.")

    def pack_bundle(self, prime_dir: pathlib.Path, dest_dir: pathlib.Path) -> pathlib.Path:
        """Pack a prime directory as a bundle."""
        bundle_path = dest_dir / f"{self._project.name}.zip"
        emit.progress(f"Packing bundle {bundle_path.name}")
        utils.build_zip(bundle_path, prime_dir)
        return bundle_path

    def pack_charm(self, prime_dir: pathlib.Path, dest_dir: pathlib.Path) -> pathlib.Path:
        """Pack a prime directory as a charm for a given set of bases."""
        charm_path = self.get_charm_path(dest_dir)
        emit.progress(f"Packing charm {charm_path.name}")
        utils.build_zip(charm_path, prime_dir)

        return charm_path

    def get_charm_path(self, dest_dir: pathlib.Path) -> pathlib.Path:
        """Get a charm file name for the appropriate set of run-on bases."""
        return dest_dir / f"{self._project.name}_{self._platform}.charm"

    @property
    def metadata(self) -> BundleMetadata | CharmMetadata:
        """Metadata model for this project."""
        if isinstance(self._project, Charm):
            return CharmMetadata.from_charm(self._project)
        if isinstance(self._project, Bundle):
            return BundleMetadata.from_bundle(self._project)
        raise NotImplementedError(f"Unknown project type {self._project.type!r}")

    def _write_file_or_object(
        self, model: dict | None, filename: str, dest_dir: pathlib.Path
    ) -> None:
        """Write a yaml file to the destination directory if the given object is not None.

        This function prefers copying the file over, but will generate YAML from the given
        model otherwise.

        :param model: The dictionary to write (or None)
        :param filename: The name of the file to copy or write.
        :param dest_dir: The path of the destination directory.
        """
        if not model:
            return
        source_path = self.project_dir / filename
        dest_path = dest_dir / filename
        if source_path.is_file():
            shutil.copyfile(source_path, dest_path)
            return
        with dest_path.open("wt+") as dest_file:
            yaml.safe_dump(model, dest_file)

    def write_metadata(self, path: pathlib.Path) -> None:
        """Write additional charm metadata.

        :param path: The path to the prime directory.
        """
        if isinstance(self._project, Charm):
            lint_results = self._services.analysis.emit_results()
            manifest = Manifest.from_charm_and_lint(self._project, lint_results)
            manifest.to_yaml_file(path / "manifest.yaml")

        project_dict = self._project.marshal()

        self._write_file_or_object(self.metadata.marshal(), "metadata.yaml", path)
        if actions := cast(Optional[dict], project_dict.get("actions")):
            self._write_file_or_object(actions, "actions.yaml", path)
        if config := cast(Optional[dict], project_dict.get("config")):
            self._write_file_or_object(config, "config.yaml", path)
