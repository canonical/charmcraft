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
import zipfile
from typing import TYPE_CHECKING

from craft_application.services import PackageService
from craft_cli import emit

from charmcraft.models.charmcraft import BasesConfiguration
from charmcraft.package import format_charm_file_name

if TYPE_CHECKING:  # pragma: no cover
    from craft_application import models


class CharmPackageService(PackageService):
    """Business logic for creating packages."""

    def pack(self, prime_dir: pathlib.Path, dest: pathlib.Path) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param prime_dir: Directory path to the prime directory.
        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        raise NotImplementedError("No general packing available yet.")

    def pack_charm(
        self, prime_dir: pathlib.Path, bases_config: BasesConfiguration
    ) -> pathlib.Path:
        """Pack a prime directory as a charm for a given set of bases."""
        zip_path = self.get_charm_path(bases_config)
        emit.progress(f"Packing charm {zip_path.name}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as charm:
            for dirpath, _dirnames, filenames in os.walk(prime_dir, followlinks=True):
                dirpath = pathlib.Path(dirpath)
                for filename in filenames:
                    filepath = dirpath / filename
                    charm.write(str(filepath), str(filepath.relative_to(prime_dir)))

        return zip_path

    def get_charm_path(self, bases_config: BasesConfiguration) -> pathlib.Path:
        """Get a charm file name for the appropriate set of run-on bases."""
        return pathlib.Path(format_charm_file_name(self._project.name, bases_config)).resolve()

    @property
    def metadata(self) -> models.BaseMetadata:
        """Metadata model for this project."""
        raise NotImplementedError("Metadata not yet handled this way")

    def write_metadata(self, path: pathlib.Path) -> None:
        """Write the project metadata to metadata.yaml in the given directory.

        :param path: The path to the prime directory.
        """
        # Right now this is a no-op until we bring in the metadata.
