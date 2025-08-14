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
"""Unit tests for the provider service."""

import functools
import pathlib
from collections.abc import Iterator
from unittest import mock

import craft_application
import pytest
from craft_cli.pytest_plugin import RecordingEmitter
from craft_providers import bases

from charmcraft.application.main import APP_METADATA
from charmcraft.services.provider import ProviderService, _maybe_lock_cache


@pytest.fixture
def provider_service(
    monkeypatch: pytest.MonkeyPatch,
    fake_path: pathlib.Path,
    service_factory: craft_application.ServiceFactory,
) -> craft_application.ProviderService:
    # Workaround for https://github.com/canonical/craft-application/issues/816
    monkeypatch.delenv("SNAP", raising=False)
    fake_cache_dir = fake_path / "cache"
    fake_cache_dir.mkdir(parents=True)

    service_factory.update_kwargs(
        "provider",
        work_dir=fake_path,
        provider_name="host",
    )

    return service_factory.get("provider")


@pytest.fixture
def mock_register(monkeypatch) -> Iterator[mock.Mock]:
    register = mock.Mock()
    monkeypatch.setattr("atexit.register", register)
    yield register

    # Call the exit hooks as if exiting the application.
    for hook in register.mock_calls:
        functools.partial(*hook.args)()


@pytest.mark.parametrize(
    "base_name",
    [
        bases.BaseName("ubuntu", "20.04"),
        bases.BaseName("ubuntu", "22.04"),
        bases.BaseName("ubuntu", "24.04"),
        bases.BaseName("ubuntu", "devel"),
        bases.BaseName("almalinux", "9"),
    ],
)
def test_get_base_forwards_cache(
    monkeypatch,
    provider_service: ProviderService,
    fake_path: pathlib.Path,
    base_name: bases.BaseName,
):
    monkeypatch.setattr(
        "charmcraft.env.get_host_shared_cache_path", lambda: fake_path / "cache"
    )

    base = provider_service.get_base(
        base_name=base_name,
        instance_name="charmcraft-test-instance",
    )

    assert base._cache_path == fake_path / "cache"


@pytest.mark.parametrize(
    "base_name",
    [
        bases.BaseName("ubuntu", "20.04"),
        bases.BaseName("ubuntu", "22.04"),
        bases.BaseName("ubuntu", "24.04"),
        bases.BaseName("ubuntu", "devel"),
        bases.BaseName("almalinux", "9"),
    ],
)
def test_get_base_no_cache_if_locked(
    monkeypatch,
    mock_register,
    tmp_path: pathlib.Path,
    base_name: bases.BaseName,
    emitter: RecordingEmitter,
):
    cache_path = tmp_path / "cache"
    cache_path.mkdir(exist_ok=True, parents=True)

    # Make a new path object to work around caching the paths and thus getting the
    # same file descriptor.
    locked = _maybe_lock_cache(cache_path)
    assert locked
    new_cache_path = pathlib.Path(str(cache_path))
    monkeypatch.setattr(
        "charmcraft.env.get_host_shared_cache_path", lambda: new_cache_path
    )

    # Can't use the fixture as pyfakefs doesn't handle locks.
    provider_service = ProviderService(
        app=APP_METADATA,
        services=None,  # pyright: ignore[reportArgumentType]
        work_dir=tmp_path,
    )

    base = provider_service.get_base(
        base_name=base_name,
        instance_name="charmcraft-test-instance",
    )

    assert base._cache_path is None
    emitter.assert_progress(
        "Shared cache locked by another process; running without cache.",
        permanent=True,
    )


def test_maybe_lock_cache_locks_single_lock(tmp_path: pathlib.Path) -> None:
    assert _maybe_lock_cache(tmp_path)


def test_maybe_lock_cache_with_another_lock(tmp_path: pathlib.Path) -> None:
    # Need to save the open file so it's not closed when we try a second time.
    first_file_descriptor = _maybe_lock_cache(tmp_path)
    assert first_file_descriptor
    assert _maybe_lock_cache(tmp_path) is None
