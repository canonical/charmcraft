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
"""General fixtures for integration tests."""
from unittest import mock

import craft_store
import pytest

from charmcraft import application, services
from charmcraft.application import commands


@pytest.fixture
def service_factory():
    factory = services.CharmcraftServiceFactory(app=application.APP_METADATA)
    factory.store.client = mock.Mock(spec_set=craft_store.StoreClient)
    return factory


@pytest.fixture
def app(monkeypatch, new_path, service_factory):
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    app = application.Charmcraft(app=application.APP_METADATA, services=service_factory)
    app._configure_services(None)
    commands.fill_command_groups(app)

    return app
