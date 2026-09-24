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
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import TYPE_CHECKING, Literal, cast

import craft_platforms
import yaml
from craft_application import services
from craft_application.services.package import package_file
from craft_application.services.state import ValueType
from craft_cli import emit
from typing_extensions import override

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

    def _project_file_path(self, filename: str) -> pathlib.Path:
        """Return the path for a project-local file."""
        return (
            self._services.get("project").resolve_project_file_path().parent / filename
        )

    def _has_reactive_plugin(self) -> bool:
        """Return whether the project uses the reactive plugin."""
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        plugins = {
            part.get("plugin") or name  # NOTE: Not the same as part.get("plugin", name)
            for name, part in project.parts.items()
        }
        return "reactive" in plugins

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

    @override
    def get_artifacts(self) -> dict[str | None, pathlib.Path]:
        """Get the output artifacts for this application."""
        return {None: self.output_dir / self.get_charm_name()}

    @override
    def write_artifacts_state(
        self, artifacts: Mapping[str | None, pathlib.Path]
    ) -> None:
        """Write artifact state for repeated pack runs."""
        platform = self._build_info.platform
        state_service = self._services.get("state")
        state_entries = cast(
            ValueType,
            [
            {"name": name, "path": str(path)} for name, path in artifacts.items()
            ],
        )
        state_service.set(
            "artifacts", platform, value=state_entries or None, overwrite=True
        )

    def read_artifacts_state(
        self, platform: str | None = None
    ) -> dict[str | None, pathlib.Path]:
        """Read artifact-oriented packaging state."""
        if platform is None:
            platform = self._build_info.platform

        state_service = self._services.get("state")

        try:
            artifacts = cast(
                list[dict[str, str | None]] | None,
                state_service.get("artifacts", platform),
            )
        except KeyError:
            artifact = cast(str | None, state_service.get("artifact", platform))
            resources = cast(
                dict[str, str] | None, state_service.get("resources", platform)
            )
            artifact_entries: list[dict[str, str | None]] = []
            if artifact:
                artifact_entries.append({"name": None, "path": artifact})
            if resources:
                artifact_entries.extend(
                    {"name": name, "path": path} for name, path in resources.items()
                )
            artifacts = artifact_entries

        return {
            artifact.get("name"): pathlib.Path(cast(str, artifact["path"]))
            for artifact in artifacts or []
            if artifact.get("path")
        }

    @override
    def _pack(self, *, name: str | None = None, path: pathlib.Path) -> None:
        """Pack the prime directory into the given charm path."""
        del name
        prime_dir = self._services.get("lifecycle").prime_dir
        emit.progress(f"Packing charm {path.name}")
        utils.build_zip(path, prime_dir)

    def get_charm_name(self) -> str:
        """Get a charm file name for the appropriate set of run-on bases."""
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        name = project.name
        build_item = self._services.get("build_plan").plan()[0]
        platform = build_item.platform

        if (
            isinstance(project, PlatformCharm)
            and project.base
            and ":" not in platform
            and "@" not in platform
            and platform in const.SUPPORTED_ARCHITECTURES | {"all"}
        ):
            platform = f"{project.base}:{platform}"

        platform = platform.replace(":", "-")
        return f"{name}_{platform}.charm"

    @property
    def metadata(self) -> CharmMetadata:
        """Metadata model for this project."""
        return CharmMetadata.from_charm(
            cast("BasesCharm | PlatformCharm", self._services.get("project").get())
        )

    @package_file(const.METADATA_FILENAME)
    def get_metadata_yaml(self, partition: str | None = None) -> str | Literal[False]:
        """Get the mediated metadata.yaml contents."""
        metadata_path = self._project_file_path(const.METADATA_FILENAME)

        if self._has_reactive_plugin():
            stage_dir = self._services.get("lifecycle").project_info.dirs.stage_dir
            if (stage_dir / const.METADATA_FILENAME).exists():
                emit.debug(
                    f"{const.METADATA_FILENAME!r} generated by charm. Not using original project metadata."
                )
                return False
            if metadata_path.is_file():
                return metadata_path.read_text()
            return self.metadata.to_yaml_string()

        if metadata_path.is_file():
            return metadata_path.read_text()

        return self.metadata.to_yaml_string()

    @package_file(const.JUJU_ACTIONS_FILENAME)
    def get_actions_yaml(
        self, partition: str | None = None
    ) -> str | None | Literal[False]:
        """Get the mediated actions.yaml contents."""
        return self._get_mediated_yaml("actions", const.JUJU_ACTIONS_FILENAME)

    @package_file(const.JUJU_CONFIG_FILENAME)
    def get_config_yaml(
        self, partition: str | None = None
    ) -> str | None | Literal[False]:
        """Get the mediated config.yaml contents."""
        return self._get_mediated_yaml("config", const.JUJU_CONFIG_FILENAME)

    def _get_mediated_yaml(
        self, project_key: str, filename: str
    ) -> str | None | Literal[False]:
        """Get the mediated contents of an optional project YAML file.

        If the given key is absent from the project model and no reactive
        charm generates the file, no file is generated - even if a
        project-local file exists. Returns False only when a reactive charm has
        already generated the file in prime; returns None when the file should
        be absent from the packaged charm.

        Precedence:
        1. A file generated by a reactive charm in the stage directory.
        2. If the key is absent from the project model, nothing.
        3. A project-local file of the given name.
        4. The contents of the given key from the project model.
        """
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        project_dict = project.marshal()
        value = cast(dict | None, project_dict.get(project_key))

        if self._has_reactive_plugin():
            stage_dir = self._services.get("lifecycle").project_info.dirs.stage_dir
            if (stage_dir / filename).exists():
                emit.debug(f"{filename!r} generated by charm. Skipping generation.")
                return False

        if not value:
            return None

        file_path = self._project_file_path(filename)

        if file_path.is_file():
            return file_path.read_text()

        return yaml.safe_dump(value, sort_keys=True)

    def _get_existing_manifest_timestamp(self) -> str | None:
        """Get the charmcraft_started_at timestamp from an existing manifest.

        Returns the timestamp if a manifest.yaml exists in the prime directory,
        or None if no manifest exists. This enables stable timestamps across
        repeated pack runs when the lifecycle is skipped.
        """
        prime_dir = self._services.get("lifecycle").prime_dir
        manifest_path = prime_dir / const.MANIFEST_FILENAME
        if manifest_path.is_file():
            try:
                existing = yaml.safe_load(manifest_path.read_text())
                if isinstance(existing, dict):
                    started_at = existing.get("charmcraft-started-at")
                    if started_at is not None:
                        if isinstance(started_at, datetime | date):
                            return started_at.isoformat()
                        return str(started_at)
            except yaml.YAMLError:
                pass
        return None

    def _get_ignored_manifest_checks(
        self, project: BasesCharm | PlatformCharm
    ) -> set[str]:
        """Get ignored lint and attribute checks for manifest generation."""
        if not project.analysis:
            return set()

        return {
            *project.analysis.ignore.linters,
            *project.analysis.ignore.attributes,
        }

    def _render_manifest_yaml(self, manifest: Manifest) -> str:
        """Render manifest.yaml contents.

        We need to include unset/default values in order to ensure that the
        architecture is included on each base in the manifest, even when the
        architectures are inferred. However, we also need to exclude Nones so that
        image-info isn't included in manifest.yaml if it doesn't exist.
        """
        return utils.dump_yaml(
            manifest.model_dump(
                mode="json",
                by_alias=True,
                exclude_unset=False,
                exclude_none=True,
            )
        )

    @package_file(const.MANIFEST_FILENAME)
    def get_manifest_yaml(self, partition: str | None = None) -> str:
        """Get the mediated manifest.yaml contents.

        This method is decorated with @package_file to participate in the
        conditional repack logic. For timestamp stability, the charmcraft_started_at
        value is reused from the existing manifest when available, preventing
        unnecessary repacks on repeated pack runs.
        """
        project = cast(
            "BasesCharm | PlatformCharm", self._services.get("project").get()
        )
        analysis_svc = cast("AnalysisService", self._services.get("analysis"))
        lint_results = list(
            analysis_svc.lint_directory(
                self._services.get("lifecycle").prime_dir,
                ignore=self._get_ignored_manifest_checks(project),
            )
        )

        started_at = self._get_existing_manifest_timestamp()
        if started_at is None:
            started_at = str(
                self._services.get("state").get("charmcraft", "started_at")
            )

        return self._render_manifest_yaml(
            self.get_manifest(lint_results, started_at=started_at)
        )

    @override
    def update_project(self) -> None:
        """Update project fields with dynamic values set during the lifecycle."""
        super().update_project()

    def get_manifest(
        self,
        lint_results: Iterable[lint.CheckResult],
        *,
        started_at: str | None = None,
    ) -> Manifest:
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

        if started_at is None:
            started_at = str(
                self._services.get("state").get("charmcraft", "started_at")
            )

        return Manifest(
            charmcraft_version=charmcraft.__version__,
            charmcraft_started_at=started_at,
            analysis={"attributes": attributes},
            image_info=image_info,
            bases=bases,
        )

    @override
    def _app_needs_repack(self, partition: str | None = None) -> bool:
        """Detect post-prime changes that occur before mediated packing runs."""
        artifact_path = self.get_artifacts()[partition]
        if not artifact_path.exists():
            return True

        prime_dir = self._prime_dir_for(partition)
        dispatch_path = prime_dir / const.DISPATCH_FILENAME
        return (
            dispatch_path.exists()
            and dispatch_path.stat().st_mtime_ns > artifact_path.stat().st_mtime_ns
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
