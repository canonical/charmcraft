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
"""Integration tests for the provider service."""

import pathlib
import sys

import pytest
from craft_application.models import BuildInfo
from craft_cli.pytest_plugin import RecordingEmitter

from charmcraft import services
from charmcraft.services.provider import _maybe_lock_cache


@pytest.mark.skipif(sys.platform == "win32", reason="no cache on windows")
def test_locks_cache(
    service_factory: services.CharmcraftServiceFactory,
    tmp_path: pathlib.Path,
    default_build_info: BuildInfo,
    emitter: RecordingEmitter,
):
    _maybe_lock_cache(tmp_path)
    assert (tmp_path / "charmcraft.lock").exists()
    provider = service_factory.provider
    provider_kwargs = {
        "build_info": default_build_info,
        "work_dir": pathlib.Path(__file__).parent,
        "cache_path": tmp_path,
    }

    with provider.instance(**provider_kwargs) as instance:
        # Because we've already locked the cache, we shouldn't see the lockfile.
        lock_test = instance.execute_run(["test", "-f", "/root/.cache/charmcraft.lock"])
        assert lock_test.returncode == 1

        # Create a file in the cache and ensure it's not visible in the outer fs
        instance.execute_run(["touch", "/root/.cache/cache_cached"])
        assert not (tmp_path / "cache_cached").exists()
