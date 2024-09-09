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
"""Configuration for services integration tests."""
import contextlib
import sys

import pyfakefs.fake_filesystem
import pytest

from charmcraft import services
from charmcraft.application.main import APP_METADATA, Charmcraft


@pytest.fixture
def service_factory(
    fs: pyfakefs.fake_filesystem.FakeFilesystem, fake_path, simple_charm
) -> services.CharmcraftServiceFactory:
    fake_project_dir = fake_path / "project"
    fake_project_dir.mkdir()

    # Allow access to the real venv library path.
    # This is necessary because certifi lazy-loads the certificate file.
    for python_path in sys.path:
        if not python_path:
            continue
        with contextlib.suppress(OSError):
            fs.add_real_directory(python_path)

    factory = services.CharmcraftServiceFactory(app=APP_METADATA)

    app = Charmcraft(app=APP_METADATA, services=factory)

    app._configure_services(provider_name=None)

    factory.project = simple_charm

    return factory
