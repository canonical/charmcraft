# Copyright 2026 Canonical Ltd.
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

"""Unit tests for remote-build"""

import argparse

from pytest_mock import MockerFixture

from charmcraft import services
from charmcraft.application import APP_METADATA
from charmcraft.application.commands.remote import RemoteBuild
from charmcraft.services.project import ProjectService


def test_remote_build_project_name_attr_regression(
    mocker: MockerFixture, service_factory: services.ServiceFactory
) -> None:
    """Regression test for https://github.com/canonical/charmcraft/issues/2598

    The project service was being erroneously cast as the project model, causing
    a later access to the `.name` field not be caught by linters.
    """
    remote_build_cmd = RemoteBuild({"app": APP_METADATA, "services": service_factory})
    namespace = argparse.Namespace(
        launchpad_accept_public_upload=True,
        recover=False,
        launchpad_timeout=0,
    )
    mocker.patch("charmcraft.services.remotebuild.RemoteBuildService")
    project_spy = mocker.spy(ProjectService, "get")

    remote_build_cmd.run(namespace)

    project_spy.assert_called_once()
