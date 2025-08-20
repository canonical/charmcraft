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

"""Service class for creating providers."""

from __future__ import annotations

import contextlib
import fcntl
import io
import os
import pathlib
from collections.abc import Callable, Generator
from typing import cast

import craft_application
import craft_platforms
import craft_providers
from craft_application import services
from craft_cli import emit
from craft_providers import bases
from typing_extensions import override

from charmcraft import env


class ProviderService(services.ProviderService):
    """Business logic for getting providers."""

    def __init__(
        self,
        app: craft_application.AppMetadata,
        services: craft_application.ServiceFactory,
        *,
        work_dir: pathlib.Path,
        provider_name: str | None = None,
        install_snap: bool = True,
    ) -> None:
        super().__init__(
            app,
            services,
            work_dir=work_dir,
            provider_name=provider_name,
            install_snap=install_snap,
        )
        self._cache_path: pathlib.Path | None = None
        self._lock: io.TextIOBase | None = None

    def setup(self) -> None:
        """Set up the provider service for Charmcraft."""
        super().setup()

        # Forward all charmcraft environment variables
        for key, value in os.environ.items():
            if key.startswith("CHARMCRAFT_"):
                self.environment[key] = value

        self.environment["CHARMCRAFT_MANAGED_MODE"] = "1"

    def get_base(
        self,
        base_name: bases.BaseName,
        *,
        instance_name: str,
        **kwargs: bool | str | None | pathlib.Path,
    ) -> craft_providers.Base:
        """Get the base configuration from a base name.

        :param base_name: The base to lookup.
        :param instance_name: A name to assign to the instance.
        :param kwargs: Additional keyword arguments are sent directly to the base.

        If no cache_path is included, adds one.
        """
        self._cache_path = cast(
            pathlib.Path, kwargs.get("cache_path", env.get_host_shared_cache_path())
        )
        self._lock = _maybe_lock_cache(self._cache_path)

        # Forward the shared cache path.
        kwargs["cache_path"] = self._cache_path if self._lock else None
        return super().get_base(
            base_name,
            instance_name=instance_name,
            # craft-application annotation is incorrect
            **kwargs,  # type: ignore[arg-type]
        )

    @override
    @contextlib.contextmanager
    def instance(
        self,
        build_info: craft_platforms.BuildInfo,
        *,
        work_dir: pathlib.Path,
        allow_unstable: bool = True,
        clean_existing: bool = False,
        use_base_instance: bool = True,
        project_name: str | None = None,
        prepare_instance: Callable[[craft_providers.Executor], None] | None = None,
        **kwargs: bool | str | None,
    ) -> Generator[craft_providers.Executor, None, None]:
        """Instance override for Charmcraft."""
        with super().instance(
            build_info,
            work_dir=work_dir,
            allow_unstable=allow_unstable,
            clean_existing=clean_existing,
            prepare_instance=prepare_instance,
            project_name=project_name,
            **kwargs,  # type: ignore[arg-type]
        ) as instance:
            try:
                instance.execute_run(["chmod", "a+rwx", "/tmp/craft-state"])
                # Use /root/.cache even if we're in the snap.
                instance.execute_run(
                    ["rm", "-rf", "/root/snap/charmcraft/common/cache"], check=True
                )
                instance.execute_run(["mkdir", "-p", "/root/.cache"], check=True)
                instance.execute_run(
                    ["ln", "-s", "/root/.cache", "/root/snap/charmcraft/common/cache"],
                    check=True,
                )
                yield instance
            finally:
                if self._lock:
                    fcntl.flock(self._lock, fcntl.LOCK_UN)
                    self._lock.close()


def _maybe_lock_cache(path: pathlib.Path) -> io.TextIOBase | None:
    """Lock the cache so we only have one copy of Charmcraft using it at a time."""
    cache_lock_path = path / "charmcraft.lock"

    emit.trace("Attempting to lock the cache path")
    lock_file = cache_lock_path.open("w+")
    try:
        # Exclusive lock, but non-blocking.
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        emit.progress(
            "Shared cache locked by another process; running without cache.",
            permanent=True,
        )
        return None
    else:
        pid = str(os.getpid())
        lock_file.write(pid)
        lock_file.flush()
        os.fsync(lock_file.fileno())
        emit.trace(f"Cache path locked by this process ({pid})")
        return lock_file
