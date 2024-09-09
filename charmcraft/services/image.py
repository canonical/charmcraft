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
"""Service class for handling OCI images."""

import dataclasses
import io
import logging
import subprocess
from collections.abc import Sequence

import craft_application
import docker  # type: ignore[import-untyped]
import docker.errors  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
from overrides import override

from charmcraft import const, errors, utils

logger = logging.getLogger("charmcraft")


@dataclasses.dataclass(frozen=True)
class OCIMetadata:
    """Metadata about an OCI image.

    :param path: A skopeo-compatible image path
    :param digest: A digest string for the image
    :param architectures: A list of architectures for Linux platforms of the image.
    """

    path: str
    digest: str
    architectures: Sequence[const.CharmArch]


class ImageService(craft_application.AppService):
    """Service to handle OCI images.

    This service is mostly a craft-application friendly wrapper around skopeo.
    Use of this service requires the app to have access to skopeo.
    """

    _skopeo: utils.Skopeo
    _docker: docker.DockerClient

    @override
    def setup(self) -> None:
        """Set up the image service."""
        super().setup()
        self._skopeo = utils.Skopeo(insecure_policy=True)
        self._docker = docker.from_env()

    def copy(
        self,
        source_image: str,
        destination_image: str,
        stdout: io.FileIO,
        *,
        dest_username: str | None = None,
        dest_password: str | None = None,
    ):
        """Use Skopeo to copy an image.

        :param source_image: A skopeo-accepted source image string.
        :param destination_image: A skopeo-accepted destination image string.
        :param stdout: A stream to use as skopeo's stdout

        This is designed to be used with craft-cli's emit.open_stream or similar.
        For example:
        >>> with emit.open_stream("Uploading image") as stream:
        ...     image_service.copy(source, dest, stdout=stream)
        However, it can be used in other ways by passing any file-like object as the stream.
        """
        self._skopeo.copy(
            source_image=source_image,
            destination_image=destination_image,
            stdout=stdout,
            stderr=subprocess.PIPE,
            dest_username=dest_username,
            dest_password=dest_password,
            preserve_digests=True,
        )

    def get_maybe_id_from_docker(self, name: str) -> str | None:
        """Get the ID of an image from Docker.

        :param name: Any string Docker recognises as the image name.
        :returns: An image digest or None

        The digest will match the OCI digest spec:
        https://github.com/opencontainers/image-spec/blob/main/descriptor.md#digests
        """
        try:
            image = self._docker.images.get(name)
        except docker.errors.ImageNotFound:
            return None
        return image.id

    def inspect(self, image: str) -> OCIMetadata:
        """Inspect an image with Skopeo and return the relevant metadata.

        :param image: A skopeo-friendly image name
        :returns: An OCIMetadata object containing metadata about the image.
        """
        try:
            raw_manifest = self._skopeo.inspect(image, raw=True)
            image_info = self._skopeo.inspect(image)
        except errors.SubprocessError as exc:
            raise errors.CraftError(
                "Could not inspect OCI image.", details=f"{exc.message}\n{exc.details}"
            )
        try:
            image_digest = image_info["Digest"]
        except KeyError:
            raise errors.CraftError("Could not get digest for image.")
        if "manifests" in raw_manifest:  # Multi-arch OCI image
            architectures: list[const.CharmArch] = []
            for child in raw_manifest["manifests"]:
                platform = child.get("platform", {})
                if platform.get("os") != "linux":
                    continue
                architectures.append(const.CharmArch(platform["architecture"]))
            if not architectures:
                raise errors.CraftError("No architectures found in image for Linux OS.")
        else:
            architectures = [const.CharmArch(image_info["Architecture"])]

        return OCIMetadata(
            path=image,
            digest=image_digest,
            architectures=architectures,
        )
