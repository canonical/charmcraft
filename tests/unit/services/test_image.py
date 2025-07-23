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

from charmcraft import application, const, utils
from charmcraft.errors import SkopeoError
from charmcraft.services.image import ImageService, OCIMetadata


@pytest.fixture
def mock_docker() -> mock.Mock:
    return mock.Mock(spec_set=docker.DockerClient)


@pytest.fixture
def mock_skopeo(fake_process) -> mock.Mock:
    fake_process.register(["/skopeo", "--version"])
    return mock.Mock(wraps=utils.Skopeo(skopeo_path="/skopeo"))


@pytest.fixture
def image_service(service_factory, mock_skopeo, mock_docker) -> ImageService:
    service = ImageService(app=application.APP_METADATA, services=service_factory)
    service._skopeo = mock_skopeo
    service._docker = mock_docker
    return service


@pytest.mark.parametrize(
    ("url", "name"),
    [
        (
            "docker://hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
            "hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
        ),
        (
            "hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
            "hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
        ),
        (
            "docker://ghcr.io/canonical/charmed-mysql@sha256:89b8305613f6ce94f78a7c9b4baedef78f2816fd6bc74c00f6607bc5e57bd8e6",
            "ghcr.io/canonical/charmed-mysql@sha256:89b8305613f6ce94f78a7c9b4baedef78f2816fd6bc74c00f6607bc5e57bd8e6",
        ),
        (
            "docker://quay.io/prometheus/blackbox-exporter:v0.24.0",
            "quay.io/prometheus/blackbox-exporter:v0.24.0",
        ),
        (
            "docker://quay.io/prometheus/blackbox-exporter:v0.24.0@sha256:3af31f8bd1ad2907b4b0f7c485fde3de0a8ee0b498d42fc971f0698885c03acb",
            "quay.io/prometheus/blackbox-exporter:v0.24.0@sha256:3af31f8bd1ad2907b4b0f7c485fde3de0a8ee0b498d42fc971f0698885c03acb",
        ),
    ],
)
def test_get_name_from_url(url: str, name: str):
    assert ImageService.get_name_from_url(url) == name


@pytest.mark.parametrize(
    ("go_arch", "charm_arch"),
    [
        *(
            (key, const.CharmArch(value))
            for key, value in const.GO_ARCH_TO_CHARM_ARCH.items()
        ),
        ("amd64", "amd64"),
        ("arm64", "arm64"),
        ("riscv64", "riscv64"),
        ("s390x", "s390x"),
    ],
)
def test_convert_go_arch_to_charm_arch(go_arch: str, charm_arch: const.CharmArch):
    assert ImageService.convert_go_arch_to_charm_arch(go_arch) == charm_arch


def test_get_maybe_id_from_docker_success(image_service: ImageService, mock_docker):
    expected = "sha256:some-sha-hash"
    mock_docker.images.get.return_value = docker.models.images.Image(
        attrs={"Id": expected}
    )

    result = image_service.get_maybe_id_from_docker("some-image")

    mock_docker.images.get.assert_called_once_with("some-image")
    assert result == expected


def test_get_maybe_id_from_docker_failure(image_service: ImageService, mock_docker):
    mock_docker.images.get.side_effect = docker.errors.ImageNotFound("womp womp")

    assert image_service.get_maybe_id_from_docker("some-image") is None


def test_get_maybe_id_from_docker_no_docker(image_service: ImageService):
    image_service._docker = None

    assert image_service.get_maybe_id_from_docker("some-image") is None


@pytest.mark.parametrize("image", ["my-image"])
@pytest.mark.parametrize("architecture", const.CharmArch)
def test_inspect_single_arch(
    fake_process,
    image_service: ImageService,
    mock_skopeo,
    image: str,
    architecture,
):
    fake_process.register(
        ["/skopeo", "inspect", "--raw", image],
        stdout=json.dumps({"raw_manifest": True}),
    )
    fake_process.register(
        ["/skopeo", "inspect", image],
        stdout=json.dumps({"Digest": "Reader's", "Architecture": architecture}),
    )

    actual = image_service.inspect(image)

    assert actual == OCIMetadata(
        path=image, digest="Reader's", architectures=[architecture]
    )


@pytest.mark.parametrize("image", ["my-image"])
@pytest.mark.parametrize("architectures", itertools.product(const.CharmArch, repeat=2))
def test_inspect_two_arch(
    fake_process,
    image_service: ImageService,
    mock_skopeo,
    image: str,
    architectures,
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

    assert actual == OCIMetadata(
        path=image, digest="Reader's", architectures=list(architectures)
    )


@pytest.mark.parametrize("image", ["my-image"])
@pytest.mark.parametrize(
    ("stderr", "error_msg"),
    [
        (
            'time="2025-06-25T19:14:57-04:00" level=fatal msg="Error parsing image name \\"docker://ghcr.io/canonical/spark-integration-hub:3.4-22.04_edge@sha256:0b9a40435440256b1c10020bd59d19e186ea68d8973fc8f2310010f9bd4e3459\\": Docker references with both a tag and digest are currently not supported"',
            "Docker references with both a tag and digest are currently not supported",
        ),
        ("level=fatal error='No message'", "Unknown error from skopeo."),
        ("Something unparsable", "Unknown error from skopeo."),
    ],
)
def test_inspect_skopeo_error(
    fake_process,
    image_service: ImageService,
    mock_skopeo,
    image: str,
    stderr: str,
    error_msg: str,
):
    fake_process.register(
        ["/skopeo", "inspect", "--raw", image],
        stdout="",
        stderr=stderr,
        returncode=1,
    )

    with pytest.raises(SkopeoError) as exc_info:
        image_service.inspect(image)

    assert error_msg in str(exc_info.value)
