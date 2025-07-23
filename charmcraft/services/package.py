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

import craft_platforms
import yaml
from craft_application import services
from craft_cli import emit

import charmcraft
from charmcraft import const, errors, models, utils
from charmcraft.models import lint
from charmcraft.models.manifest import Attribute, Manifest
from charmcraft.models.metadata import CharmMetadata
from charmcraft.models.project import (
    BasesCharm,
    PlatformCharm,
)

if TYPE_CHECKING:
    from charmcraft.services.analysis import AnalysisService


class PackageService(services.PackageService):
    """Business logic for creating packages."""

    def pack(self, prime_dir: pathlib.Path, dest: pathlib.Path) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param prime_dir: Directory path to the prime directory.
        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        return [self.pack_charm(prime_dir, dest)]

    def pack_charm(
        self, prime_dir: pathlib.Path, dest_dir: pathlib.Path
    ) -> pathlib.Path:
        """Pack a prime directory as a charm for a given set of bases."""
        charm_name = self.get_charm_name()
        charm_path = dest_dir / charm_name
        emit.progress(f"Packing charm {charm_name}")
        utils.build_zip(charm_path, prime_dir)

        return charm_path

    def get_charm_name(self) -> str:
        """Get a charm file name for the appropriate set of run-on bases."""
        name = self._services.get("project").get().name
        platform = self._services.get("build_plan").plan()[0].platform
        platform = platform.replace(":", "-")
        return f"{name}_{platform}.charm"

    @property
    def metadata(self) -> CharmMetadata:
        """Metadata model for this project."""
        return CharmMetadata.from_charm(
            cast("BasesCharm | PlatformCharm", self._services.get("project").get())
        )

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
        source_path = (
            self._services.get("project").resolve_project_file_path().parent / filename
        )
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
            charmcraft_started_at=str(
                self._services.get("state").get("charmcraft", "started_at")
            ),
            analysis={"attributes": attributes},
            image_info=image_info,
            bases=bases,
        )

    def get_manifest_bases(self) -> list[models.Base]:
        """Get the bases used for a charm manifest from the project."""
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        build_item = self._services.get("build_plan").plan()[0]
        if isinstance(project, BasesCharm):
            run_on_bases = []
            for project_base in project.bases:
                for build_base in project_base.build_on:
                    if build_base.name != build_item.build_base.distribution:
                        continue
                    if build_base.channel != build_item.build_base.series:
                        continue
                    if build_item.build_on not in build_base.architectures:
                        continue
                    run_on_bases.extend(project_base.run_on)
            if not run_on_bases:
                raise RuntimeError("Could not determine run-on bases.")
            return run_on_bases
        if isinstance(project, PlatformCharm):
            archs = [str(build_item.build_for)]

            # single base recipes will have a base
            if project.base:
                return [models.Base.from_str_and_arch(project.base, archs)]

            # multi-base recipes may have the base in the platform name
            platform_label = build_item.platform
            if base := craft_platforms.parse_base_and_name(platform_label)[0]:
                return [
                    models.Base(
                        name=base.distribution,
                        channel=base.series,
                        architectures=archs,
                    )
                ]

            # Otherwise, retrieve the build-for base from the platform in the project.
            # This complexity arises from building on devel bases - the BuildInfo
            # contains the devel base and not the compatibility base.
            platform = project.platforms.get(platform_label)
            if platform and platform.build_for:
                if base := craft_platforms.parse_base_and_architecture(
                    platform.build_for[0]
                )[0]:
                    return [
                        models.Base(
                            name=base.distribution,
                            channel=base.series,
                            architectures=archs,
                        )
                    ]

        raise TypeError(f"Unknown charm type {project.__class__}, cannot get bases.")

    def write_metadata(self, path: pathlib.Path) -> None:
        """Write additional charm metadata.

        :param path: The path to the prime directory.
        """
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        path.mkdir(parents=True, exist_ok=True)
        if isinstance(project, BasesCharm | PlatformCharm):
            if project.analysis:
                ignore_checkers = {
                    *project.analysis.ignore.linters,
                    *project.analysis.ignore.attributes,
                }
            else:
                ignore_checkers = set()
            svc = cast("AnalysisService", self._services.get("analysis"))
            lint_results = svc.lint_directory(
                self._services.get("lifecycle").prime_dir, ignore=ignore_checkers
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
                        mode="json",
                        by_alias=True,
                        exclude_unset=False,
                        exclude_none=True,
                    )
                )
            )

        project_dict = project.marshal()

        # If there is a reactive part, defer to it for the existence of metadata.yaml.
        plugins = {
            part.get("plugin") or name  # NOTE: Not the same as part.get("plugin", name)
            for name, part in project.parts.items()
        }
        is_reactive = "reactive" in plugins
        stage_dir = self._services.get("lifecycle").project_info.dirs.stage_dir
        if is_reactive and (stage_dir / const.METADATA_FILENAME).exists():
            emit.debug(
                f"{const.METADATA_FILENAME!r} generated by charm. Not using original project metadata."
            )
        else:
            self._write_file_or_object(
                self.metadata.marshal(), const.METADATA_FILENAME, path
            )
        if is_reactive and (stage_dir / const.JUJU_ACTIONS_FILENAME).exists():
            emit.debug(
                f"{const.JUJU_ACTIONS_FILENAME!r} generated by charm. Skipping generation."
            )
        elif actions := cast(dict | None, project_dict.get("actions")):
            self._write_file_or_object(actions, "actions.yaml", path)
        if is_reactive and (stage_dir / const.JUJU_CONFIG_FILENAME).exists():
            emit.debug(
                f"{const.JUJU_CONFIG_FILENAME!r} generated by charm. Skipping generation."
            )
        elif config := cast(dict | None, project_dict.get("config")):
            self._write_file_or_object(config, "config.yaml", path)
