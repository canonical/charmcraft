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
"""Integration tests for the Image service."""

import pytest

from charmcraft import application
from charmcraft.services.image import ImageService


@pytest.fixture
def image_service() -> ImageService:
    service = ImageService(
        app=application.APP_METADATA,
        services=None,  # pyright: ignore[reportArgumentType]
    )
    service.setup()
    return service


@pytest.mark.parametrize(
    "url",
    [
        "docker://hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
        "hello-world@sha256:18a657d0cc1c7d0678a3fbea8b7eb4918bba25968d3e1b0adebfa71caddbc346",
        "docker://ghcr.io/canonical/charmed-mysql@sha256:89b8305613f6ce94f78a7c9b4baedef78f2816fd6bc74c00f6607bc5e57bd8e6",
        "docker://quay.io/prometheus/blackbox-exporter:v0.24.0",
        "docker://quay.io/prometheus/blackbox-exporter:v0.24.0@sha256:3af31f8bd1ad2907b4b0f7c485fde3de0a8ee0b498d42fc971f0698885c03acb",
    ],
)
def test_get_maybe_id_from_docker_no_exceptions(image_service: ImageService, url):
    image_service.get_maybe_id_from_docker(url)
