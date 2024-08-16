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
"""Integration tests for the store service."""


import pytest

from charmcraft import models, services


@pytest.fixture
def store_service(service_factory):
    return service_factory.store


@pytest.mark.parametrize(
    "libraries",
    [
        [models.CharmLib(lib="observability-libs.cert_handler", version="1")],
        [models.CharmLib(lib="observability-libs.cert_handler", version="1.8")],
    ],
)
def test_get_libraries(store_service: services.StoreService, libraries):
    libraries_response = store_service.get_libraries_metadata(libraries)
    assert len(libraries_response) == len(libraries)
    for lib in libraries_response:
        full_lib = store_service.get_library(
            lib.charm_name, library_id=lib.lib_id, api=lib.api, patch=lib.patch
        )
        assert full_lib.content is not None
        assert full_lib.content_hash == lib.content_hash
