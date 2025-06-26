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
    _docker: docker.DockerClient | None

    @override
    def setup(self) -> None:
        """Set up the image service."""
        super().setup()
        self._skopeo = utils.Skopeo(insecure_policy=True)
        try:
            self._docker = docker.from_env()
        except docker.errors.DockerException:
            logger.debug(
                "could not create Docker client. Docker may not be installed. Ignoring..."
            )
            self._docker = None

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
            # all_images allows uploading multi-arch OCI images.
            all_images=True,
        )

    @staticmethod
    def get_name_from_url(url: str) -> str:
        """Get the name of an image from a Docker URL or its name."""
        if "://" not in url:
            return url
        # Return only the name, even if something is on ghcr or somewhere.
        return url.partition("://")[2]

    def get_maybe_id_from_docker(self, url: str) -> str | None:
        """Get the ID of an image from Docker.

        :param url: Any string Docker recognises as the image name or a docker:// url
        :returns: An image digest or None

        The digest will match the OCI digest spec:
        https://github.com/opencontainers/image-spec/blob/main/descriptor.md#digests
        """
        if self._docker is None:
            return None
        name = self.get_name_from_url(url)
        try:
            image = self._docker.images.get(name)
        except docker.errors.ImageNotFound:
            logger.debug("Image not found in local Docker")
        except docker.errors.APIError as exc:
            logger.debug(f"API error when querying local Docker: {exc}", exc_info=exc)
        else:
            return image.id
        return None

    @staticmethod
    def convert_go_arch_to_charm_arch(architecture: str) -> const.CharmArch:
        """Convert an OCI architecture to a charm architecture."""
        return const.CharmArch(
            const.GO_ARCH_TO_CHARM_ARCH.get(architecture, architecture)
        )

    def inspect(self, image: str) -> OCIMetadata:
        """Inspect an image with Skopeo and return the relevant metadata.

        :param image: A skopeo-friendly image name
        :returns: An OCIMetadata object containing metadata about the image.
        """
        raw_manifest = self._skopeo.inspect(image, raw=True)
        image_info = self._skopeo.inspect(image)

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
                arch = platform["architecture"]
                try:
                    charm_arch = self.convert_go_arch_to_charm_arch(arch)
                except ValueError:
                    logger.debug(f"Ignoring unknown architecture {arch}")
                    continue
                architectures.append(charm_arch)
            if not architectures:
                raise errors.CraftError("No architectures found in image for Linux OS.")
        else:
            architectures = [const.CharmArch(image_info["Architecture"])]

        return OCIMetadata(
            path=image,
            digest=image_digest,
            architectures=architectures,
        )
