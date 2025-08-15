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
import shutil
import subprocess
import sys

import craft_application
import pytest
from craft_cli.pytest_plugin import RecordingEmitter
from craft_platforms import BuildInfo

from charmcraft.services.provider import _maybe_lock_cache

pytestmark = [pytest.mark.slow]


@pytest.mark.skipif(
    sys.platform == "darwin", reason="multipass sometimes fails weirdly for this test"
)
def test_lock_cache(
    service_factory: craft_application.ServiceFactory,
    tmp_path: pathlib.Path,
    default_build_info: BuildInfo,
    emitter: RecordingEmitter,
):
    cache_path = tmp_path / "cache"
    cache_path.mkdir()
    lock_file = cache_path / "charmcraft.lock"
    bash_lock_cmd = (
        ["bash", "-c", f"flock -n {lock_file} true"] if shutil.which("flock") else None
    )
    provider = service_factory.provider
    provider_kwargs = {
        "build_info": default_build_info,
        "work_dir": tmp_path,
        "cache_path": cache_path,
    }
    assert not lock_file.exists()

    with provider.instance(**provider_kwargs):
        # Test that the cache lock gets created
        assert lock_file.is_file()
        if bash_lock_cmd:
            with pytest.raises(subprocess.CalledProcessError):
                # Another process should not be able to lock the file.
                subprocess.run(bash_lock_cmd, check=True)

    # After exiting we should be able to lock the file.
    if bash_lock_cmd:
        subprocess.run(bash_lock_cmd, check=True)


@pytest.mark.skipif(
    sys.platform == "darwin", reason="multipass sometimes fails weirdly for this test"
)
def test_locked_cache_no_cache(
    service_factory: craft_application.ServiceFactory,
    tmp_path: pathlib.Path,
    default_build_info: BuildInfo,
    emitter: RecordingEmitter,
):
    cache_path = tmp_path / "cache"
    cache_path.mkdir()
    lock_file = cache_path / "charmcraft.lock"

    bash_lock_cmd = (
        ["bash", "-c", f"flock -n {lock_file} true"] if shutil.which("flock") else None
    )
    # Check that we can lock the file from another process.
    if bash_lock_cmd:
        subprocess.run(bash_lock_cmd, check=True)
    _ = _maybe_lock_cache(cache_path)
    # And now we can't.
    if bash_lock_cmd:
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.run(bash_lock_cmd, check=True)

    provider = service_factory.provider
    provider_kwargs = {
        "build_info": default_build_info,
        "work_dir": tmp_path,
        "cache_path": cache_path,
    }

    with provider.instance(**provider_kwargs) as instance:
        # Create a file in the cache and ensure it's not visible in the outer fs
        instance.execute_run(["touch", "/root/.cache/cache_cached"])

        # Because we've already locked the cache, we don't get a subdirectory in
        # the cache, and thus the touch command inside there only affected the
        # instance cache and not the shared cache.
        assert list(cache_path.iterdir()) == [cache_path / "charmcraft.lock"]
        emitter.assert_progress(
            "Shared cache locked by another process; running without cache.",
            permanent=True,
        )

        assert not (tmp_path / "cache_cached").exists()


@pytest.mark.skipif(
    sys.platform == "darwin", reason="multipass sometimes fails weirdly for this test"
)
def test_cache_symlink(
    service_factory: craft_application.ServiceFactory,
    tmp_path: pathlib.Path,
    default_build_info: BuildInfo,
    emitter: RecordingEmitter,
):
    cache_path = tmp_path / "cache"
    cache_path.mkdir()
    provider = service_factory.provider
    provider_kwargs = {
        "build_info": default_build_info,
        "work_dir": tmp_path,
        "cache_path": cache_path,
    }
    with provider.instance(**provider_kwargs) as instance:
        instance.execute_run(["test", "-d", "/root/.cache"], check=True)
        instance.execute_run(
            ["test", "-d", "/root/snap/charmcraft/common/cache"], check=True
        )
        with pytest.raises(subprocess.CalledProcessError):
            instance.execute_run(["test", "-d", "/blorp"], check=True)
