# Copyright 2024 Canonical Ltd.
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
"""Service class for interacting with charm libraries."""

from __future__ import annotations

import pathlib

import craft_application

from charmcraft import models, utils
from charmcraft.store.models import Library


class CharmLibsService(craft_application.ProjectService):
    """Business logic for creating packages."""

    _project: models.CharmcraftProject  # type: ignore[assignment]

    def __init__(
        self,
        app: craft_application.AppMetadata,
        services: craft_application.ServiceFactory,
        *,
        project: models.CharmcraftProject,
        project_dir: pathlib.Path,
    ) -> None:
        super().__init__(app, services, project=project)
        self._project_dir = project_dir

    def is_downloaded(
        self, *, charm_name: str, lib_name: str, api: int, patch: int | None = None
    ) -> bool:
        """Check if the given charm lib is already downloaded on disk.

        :param charm_name: The name of the charm the lib is attached to.
        :param lib_name: The name of the lib itself.
        :param api: The api version of the lib
        :param patch: If given, the specific patch version of the lib.
        """
        lib_path = utils.get_lib_path(charm_name, lib_name, api)
        if not (self._project_dir / lib_path).exists():
            return False

        if patch is None:
            return True

        lib_info = utils.get_lib_info(lib_path=self._project_dir / lib_path)
        return lib_info.patch == patch

    def get_local_version(
        self, *, charm_name: str, lib_name: str
    ) -> tuple[int, int] | None:
        """Get the version of the library on the machine, or None.

        :param charm_name: The name of the charm where the lib is published
        :param lib_name: The name of the library itself
        :returns: Either the version of the library as a pair of integers or None
            if the library cannot be found.
        """
        charm_libs_path = self._project_dir / utils.get_lib_charm_path(charm_name)
        if not charm_libs_path.is_dir():
            return None
        for api_version_path in charm_libs_path.iterdir():
            lib_path = api_version_path / f"{lib_name}.py"
            if lib_path.exists() and lib_path.is_file() or lib_path.is_symlink():
                info = utils.get_lib_info(lib_path=lib_path)
                if info.patch == -1:
                    return None
                return (info.api, info.patch)
        return None

    def write(self, library: Library) -> None:
        """Write the given library to disk.

        :param library: A store library object with valid content.
        """
        if library.content is None:
            # This should be considered an internal error.
            raise ValueError("Library has no content.")
        lib_path = self._project_dir / utils.get_lib_path(
            library.charm_name, library.lib_name, library.api
        )
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        lib_path.write_text(library.content)
