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
"""Unit tests for the Image service."""


import itertools
import json
from unittest import mock

import docker
import docker.errors
import docker.models.images
import pytest

from charmcraft import application, const, services, utils


@pytest.fixture
def mock_docker() -> mock.Mock:
    return mock.Mock(spec_set=docker.DockerClient)


@pytest.fixture
def mock_skopeo(fake_process) -> mock.Mock:
    fake_process.register(["/skopeo", "--version"])
    return mock.Mock(wraps=utils.Skopeo(skopeo_path="/skopeo"))


@pytest.fixture
def image_service(service_factory, mock_skopeo, mock_docker) -> services.ImageService:
    service = services.ImageService(app=application.APP_METADATA, services=service_factory)
    service._skopeo = mock_skopeo
    service._docker = mock_docker
    return service


def test_get_maybe_id_from_docker_success(image_service: services.ImageService, mock_docker):
    expected = "sha256:some-sha-hash"
    mock_docker.images.get.return_value = docker.models.images.Image(attrs={"Id": expected})

    result = image_service.get_maybe_id_from_docker("some-image")

    mock_docker.images.get.assert_called_once_with("some-image")
    assert result == expected


def test_get_maybe_id_from_docker_failure(image_service: services.ImageService, mock_docker):
    mock_docker.images.get.side_effect = docker.errors.ImageNotFound("womp womp")

    assert image_service.get_maybe_id_from_docker("some-image") is None


@pytest.mark.parametrize("image", ["my-image"])
@pytest.mark.parametrize("architecture", const.CharmArch)
def test_inspect_single_arch(
    fake_process, image_service: services.ImageService, mock_skopeo, image: str, architecture
):
    fake_process.register(
        ["/skopeo", "inspect", "--raw", image], stdout=json.dumps({"raw_manifest": True})
    )
    fake_process.register(
        ["/skopeo", "inspect", image],
        stdout=json.dumps({"Digest": "Reader's", "Architecture": architecture}),
    )

    actual = image_service.inspect(image)

    assert actual == services.image.OCIMetadata(
        path=image, digest="Reader's", architectures=[architecture]
    )


@pytest.mark.parametrize("image", ["my-image"])
@pytest.mark.parametrize("architectures", itertools.product(const.CharmArch, repeat=2))
def test_inspect_two_arch(
    fake_process, image_service: services.ImageService, mock_skopeo, image: str, architectures
):
    fake_process.register(
        ["/skopeo", "inspect", "--raw", image],
        stdout=json.dumps(
            {
                "manifests": [
                    {"platform": {"os": "linux", "architecture": str(arch)}}
                    for arch in architectures
                ],
            }
        ),
    )
    fake_process.register(
        ["/skopeo", "inspect", image],
        stdout=json.dumps({"Digest": "Reader's", "Architecture": "amd64"}),
    )

    actual = image_service.inspect(image)

    assert actual == services.image.OCIMetadata(
        path=image, digest="Reader's", architectures=list(architectures)
    )
