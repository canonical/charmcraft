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

import os
import pathlib
import shutil
import zipfile
from typing import cast

import craft_application
import yaml
from craft_application.services import PackageService
from craft_cli import emit

from charmcraft.models import project
from charmcraft.models.charmcraft import BasesConfiguration
from charmcraft.models.manifest import Manifest
from charmcraft.models.metadata import BundleMetadata, CharmMetadata
from charmcraft.models.project import Bundle, Charm, CharmcraftProject
from charmcraft.package import format_charm_file_name


class CharmcraftPackageService(PackageService):
    """Business logic for creating packages."""

    _project: project.CharmcraftProject

    def __init__(  # (too many arguments)
        self,
        app: craft_application.AppMetadata,
        project: CharmcraftProject,
        services: craft_application.ServiceFactory,
        *,
        project_dir: pathlib.Path,
    ) -> None:
        super().__init__(app, cast(craft_application.models.Project, project), services)
        self._project_dir = project_dir.resolve(strict=True)

    def pack(self, prime_dir: pathlib.Path, dest: pathlib.Path) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param prime_dir: Directory path to the prime directory.
        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        if self._project.type == "charm":
            charm = cast(project.Charm, self._project)

            # TODO: Figure out which base we're using.
            return [self.pack_charm(prime_dir, dest, charm.bases[0])]
        raise NotImplementedError("No general packing available yet.")

    def pack_charm(
        self, prime_dir: pathlib.Path, dest_dir: pathlib.Path, bases_config: BasesConfiguration
    ) -> pathlib.Path:
        """Pack a prime directory as a charm for a given set of bases."""
        zip_path = self.get_charm_path(dest_dir, bases_config)
        emit.progress(f"Packing charm {zip_path.name}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as charm:
            for dirpath, _dirnames, filenames in os.walk(prime_dir, followlinks=True):
                dirpath = pathlib.Path(dirpath)
                for filename in filenames:
                    filepath = dirpath / filename
                    charm.write(str(filepath), str(filepath.relative_to(prime_dir)))

        return zip_path

    def get_charm_path(
        self, dest_dir: pathlib.Path, bases_config: BasesConfiguration
    ) -> pathlib.Path:
        """Get a charm file name for the appropriate set of run-on bases."""
        return dest_dir / format_charm_file_name(self._project.name, bases_config)

    @property
    def metadata(self) -> BundleMetadata | CharmMetadata:
        """Metadata model for this project."""
        if isinstance(self._project, Charm):
            return CharmMetadata.from_charm(self._project)
        if isinstance(self._project, Bundle):
            return BundleMetadata.from_bundle(self._project)
        raise NotImplementedError(f"Unknown project type {self._project.type!r}")

    def _write_file_or_object(self, model: dict, filename: str, dest_dir: pathlib.Path) -> None:
        """Write a yaml file to the destination directory if the given object is not None.

        This function prefers copying the file over, but will generate YAML from the given
        model otherwise.

        :param model: The dictionary to write (or None)
        :param filename: The name of the file to copy or write.
        :param dest_dir: The path of the destination directory.
        """
        source_path = self._project_dir / filename
        dest_path = dest_dir / filename
        if source_path.exists():
            shutil.copyfile(source_path, dest_path)
            return
        if model:
            with dest_path.open("wt+") as dest_file:
                yaml.safe_dump(model, dest_file)

    def write_metadata(self, path: pathlib.Path) -> None:
        """Write additional charm metadata.

        :param path: The path to the prime directory.
        """
        if isinstance(self._project, Charm):
            manifest = Manifest.from_charm(self._project)
            manifest.to_yaml_file(path / "manifest.yaml")

        project_dict = self._project.marshal()

        self._write_file_or_object(self.metadata.marshal(), "metadata.yaml", path)
        self._write_file_or_object(project_dict.get("actions"), "actions.yaml", path)
        self._write_file_or_object(project_dict.get("config"), "config.yaml", path)
