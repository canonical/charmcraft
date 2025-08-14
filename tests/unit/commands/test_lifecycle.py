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
"""Unit tests for lifecycle commands."""

import argparse
import pathlib
from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest
from craft_cli.pytest_plugin import RecordingEmitter

from charmcraft import application, models, services, utils
from charmcraft.application.commands import lifecycle
from charmcraft.store.models import Library

if TYPE_CHECKING:
    from charmcraft.models.project import CharmcraftProject
    from charmcraft.services.charmlibs import CharmLibsService


def get_namespace(
    *,
    bases_index=None,
    debug=False,
    destructive_mode=False,
    force=None,
    shell=False,
    shell_after=False,
    format=None,
    measure=None,
    include_all_charms: bool = False,
    include_charm: list[pathlib.Path] | None = None,
    output_bundle: pathlib.Path | None = None,
    parts: list[str] | None = None,
) -> argparse.Namespace:
    if bases_index is None:
        bases_index = []

    return argparse.Namespace(
        bases_index=bases_index,
        debug=debug,
        destructive_mode=destructive_mode,
        force=force,
        shell=shell,
        shell_after=shell_after,
        format=format,
        measure=measure,
        include_all_charms=include_all_charms,
        include_charm=include_charm,
        output_bundle=output_bundle,
        parts=parts,
    )


@pytest.fixture
def pack(service_factory: services.ServiceFactory) -> lifecycle.PackCommand:
    return lifecycle.PackCommand(
        {"app": application.APP_METADATA, "services": service_factory}
    )


def test_pack_update_charm_libs_empty(
    project_path: pathlib.Path,
    pack: lifecycle.PackCommand,
    emitter: RecordingEmitter,
    service_factory: services.ServiceFactory,
    mock_store_anonymous_client: mock.Mock,
    check,
):
    project = cast("CharmcraftProject", service_factory.get("project").get())
    project.charm_libs = [models.CharmLib(lib="my_charm.my_lib", version="0.1")]
    store_lib = Library("lib_id", "my_lib", "my_charm", 0, 1, "Lib contents", "hash")
    mock_store_anonymous_client.fetch_libraries_metadata.return_value = [store_lib]
    mock_store_anonymous_client.get_library.return_value = store_lib

    libs_service = cast("CharmLibsService", service_factory.get("charm_libs"))
    libs_service.write = mock.Mock(wraps=libs_service.write)

    pack._update_charm_libs()

    libs_service.write.assert_called_once_with(store_lib)

    with check():
        emitter.assert_debug(repr(store_lib))

    path = project_path / utils.get_lib_path("my_charm", "my_lib", 0)
    assert path.read_text() == "Lib contents"


def test_pack_update_charm_libs_no_update(
    fake_project_dir: pathlib.Path,
    pack: lifecycle.PackCommand,
    simple_charm,
    emitter: RecordingEmitter,
    service_factory: services.ServiceFactory,
    mock_store_anonymous_client: mock.Mock,
):
    simple_charm.charm_libs = [models.CharmLib(lib="my_charm.my_lib", version="0.1")]
    store_lib = Library("lib_id", "my_lib", "my_charm", 0, 1, "Lib contents", "hash")
    path = fake_project_dir / utils.get_lib_path("my_charm", "my_lib", 0)
    path.parent.mkdir(parents=True)
    path.write_text("LIBID='id'\nLIBAPI=0\nLIBPATCH=1")
    mock_store_anonymous_client.fetch_libraries_metadata.return_value = [store_lib]
    mock_store_anonymous_client.get_library.return_value = store_lib

    pack._update_charm_libs()

    with pytest.raises(AssertionError):
        emitter.assert_debug(repr(store_lib))

    assert path.read_text() != "Lib contents"


def test_pack_update_charm_libs_needs_update(
    fake_project_dir: pathlib.Path,
    pack: lifecycle.PackCommand,
    simple_charm,
    emitter: RecordingEmitter,
    service_factory: services.ServiceFactory,
    mock_store_anonymous_client: mock.Mock,
):
    simple_charm.charm_libs = [models.CharmLib(lib="my_charm.my_lib", version="0.2")]
    store_lib = Library("lib_id", "my_lib", "my_charm", 0, 2, "Lib contents", "hash")
    path = fake_project_dir / utils.get_lib_path("my_charm", "my_lib", 0)
    path.parent.mkdir(parents=True)
    path.write_text("LIBID='id'\nLIBAPI=0\nLIBPATCH=1")
    mock_store_anonymous_client.fetch_libraries_metadata.return_value = [store_lib]
    mock_store_anonymous_client.get_library.return_value = store_lib

    pack._update_charm_libs()

    with pytest.raises(AssertionError):
        emitter.assert_debug(repr(store_lib))

    assert path.read_text() != "Lib contents"
