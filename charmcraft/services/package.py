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

import json
import os
import pathlib
import shutil
from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

import craft_application
import yaml
from craft_application import services, util
from craft_cli import emit
from craft_providers import bases

import charmcraft
from charmcraft import const, errors, models, utils
from charmcraft.models import lint
from charmcraft.models.manifest import Attribute, Manifest
from charmcraft.models.metadata import BundleMetadata, CharmMetadata
from charmcraft.models.project import (
    BasesCharm,
    Bundle,
    CharmcraftProject,
    PlatformCharm,
)

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
        build_plan: list[craft_application.models.BuildInfo],
    ) -> None:
        super().__init__(app, services, project=cast(craft_application.models.Project, project))
        self.project_dir = project_dir.resolve(strict=True)
        self._platform = build_plan[0].platform
        self._build_plan = build_plan

    def pack(self, prime_dir: pathlib.Path, dest: pathlib.Path) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param prime_dir: Directory path to the prime directory.
        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        if self._project.type == "charm":
            packages = [self.pack_charm(prime_dir, dest)]
        elif self._project.type == "bundle":
            packages = [self.pack_bundle(prime_dir, dest)]
        else:
            raise NotImplementedError(f"Unknown package type {self._project.type}")

        self._write_package_paths(packages)
        return packages

    def _write_package_paths(self, packages: Iterable[pathlib.Path]) -> None:
        """Write the paths of packages to a hidden file in the project directory.

        This allows Charmcraft to output the packages to arbitrary directories on the host.
        """
        packages_file = self.project_dir / ".charmcraft_output_packages.txt"

        with packages_file.open("at") as file:
            file.writelines(f"{package.name}\n" for package in packages)

    def pack_bundle(self, prime_dir: pathlib.Path, dest_dir: pathlib.Path) -> pathlib.Path:
        """Pack a prime directory as a bundle."""
        name = self._project.name or "bundle"
        bundle_path = dest_dir / f"{name}.zip"
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
        if self._platform:
            return dest_dir / f"{self._project.name}_{self._platform}.charm"
        build_plan = models.CharmcraftBuildPlanner.model_validate(
            self._project.marshal()
        ).get_build_plan()
        platform = utils.get_os_platform()
        build_on_base = bases.BaseName(name=platform.system, version=platform.release)
        host_arch = util.get_host_architecture()
        for build_info in build_plan:
            print(build_info)
            if build_info.build_on != host_arch:
                continue
            if build_info.base == build_on_base:
                return dest_dir / f"{self._project.name}_{build_info.platform}.charm"

        raise errors.CraftError(
            "Current machine is not a valid build platform for this charm.",
        )

    @property
    def metadata(self) -> BundleMetadata | CharmMetadata:
        """Metadata model for this project."""
        if isinstance(self._project, BasesCharm | PlatformCharm):
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
        dest_dir.mkdir(parents=True, exist_ok=True)
        source_path = self.project_dir / filename
        dest_path = dest_dir / filename
        if source_path.is_file():
            shutil.copyfile(source_path, dest_path)
            return
        with dest_path.open("wt+") as dest_file:
            yaml.safe_dump(model, dest_file)

    def get_manifest(self, lint_results: Iterable[lint.CheckResult]) -> Manifest:
        """Get the manifest for this charm."""
        attributes = [
            Attribute(name=result.name, result=result.result)
            for result in lint_results
            if result.check_type == lint.CheckType.ATTRIBUTE
        ]

        if image_info := os.getenv(const.IMAGE_INFO_ENV_VAR):
            try:
                image_info = json.loads(image_info)
            except json.decoder.JSONDecodeError as exc:
                msg = f"Failed to parse the content of {const.IMAGE_INFO_ENV_VAR} environment variable"
                raise errors.CraftError(msg) from exc

        bases = self.get_manifest_bases()

        return Manifest(
            charmcraft_version=charmcraft.__version__,
            charmcraft_started_at=self._project.started_at.isoformat(),
            analysis={"attributes": attributes},
            image_info=image_info,
            bases=bases,
        )

    def get_manifest_bases(self) -> list[models.Base]:
        """Get the bases used for a charm manifest from the project."""
        if isinstance(self._project, BasesCharm):
            run_on_bases = []
            for project_base in self._project.bases:
                for build_base in project_base.build_on:
                    if build_base.name != self._build_plan[0].base.name:
                        continue
                    if build_base.channel != self._build_plan[0].base.version:
                        continue
                    if self._build_plan[0].build_on not in build_base.architectures:
                        continue
                    run_on_bases.extend(project_base.run_on)
            if not run_on_bases:
                raise RuntimeError("Could not determine run-on bases.")
            return run_on_bases
        if isinstance(self._project, PlatformCharm):
            if not self._platform:
                architectures = [util.get_host_architecture()]
            elif self._platform in (*const.SUPPORTED_ARCHITECTURES, "all"):
                architectures = [self._platform]
            elif platform := self._project.platforms.get(self._platform):
                if platform.build_for:
                    architectures = [str(arch) for arch in platform.build_for]
                else:
                    raise ValueError(f"Platform {self._platform} contains unknown build-for.")
            else:
                architectures = [util.get_host_architecture()]
            return [models.Base.from_str_and_arch(self._project.base, architectures)]
        raise TypeError(f"Unknown charm type {self._project.__class__}, cannot get bases.")

    def write_metadata(self, path: pathlib.Path) -> None:
        """Write additional charm metadata.

        :param path: The path to the prime directory.
        """
        path.mkdir(parents=True, exist_ok=True)
        if isinstance(self._project, BasesCharm | PlatformCharm):
            if self._project.analysis:
                ignore_checkers = {
                    *self._project.analysis.ignore.linters,
                    *self._project.analysis.ignore.attributes,
                }
            else:
                ignore_checkers = set()
            lint_results = self._services.analysis.lint_directory(
                self._services.lifecycle.prime_dir, ignore=ignore_checkers
            )
            manifest = self.get_manifest(lint_results)
            # Converting the manifest to a dictionary here is fairly fragile.
            # We need to include unset/default values in order to ensure that the
            # architecture is included on each base in the manifest, even when the
            # architectures are inferred. However, we also need to exclude Nones so that
            # image-info isn't included in manifest.yaml if it doesn't exist.
            # Tread carefully when changing this next line. Treat it like an antique
            # crystal wine glass.
            (path / "manifest.yaml").write_text(
                utils.dump_yaml(
                    manifest.model_dump(
                        mode="json", by_alias=True, exclude_unset=False, exclude_none=True
                    )
                )
            )

        project_dict = self._project.marshal()

        # If there is a reactive part, defer to it for the existence of metadata.yaml.
        plugins = {part.get("plugin") or name for name, part in self._project.parts.items()}
        is_reactive = "reactive" in plugins
        stage_dir = self._services.lifecycle.project_info.dirs.stage_dir
        if is_reactive and (stage_dir / const.METADATA_FILENAME).exists():
            emit.debug(
                f"{const.METADATA_FILENAME!r} generated by charm. Not using original project metadata."
            )
        else:
            self._write_file_or_object(self.metadata.marshal(), const.METADATA_FILENAME, path)
        if is_reactive and (stage_dir / const.JUJU_ACTIONS_FILENAME).exists():
            emit.debug(f"{const.JUJU_ACTIONS_FILENAME!r} generated by charm. Skipping generation.")
        elif actions := cast(dict | None, project_dict.get("actions")):
            self._write_file_or_object(actions, "actions.yaml", path)
        if config := cast(dict | None, project_dict.get("config")):
            self._write_file_or_object(config, "config.yaml", path)
