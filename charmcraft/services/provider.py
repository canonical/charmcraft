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

import atexit

try:
    import fcntl
except ModuleNotFoundError:  # Not available on Windows.
    fcntl = None  # type: ignore[assignment]
import os
import pathlib
from typing import cast

import craft_providers
from craft_application import services
from craft_cli import emit
from craft_providers import bases

from charmcraft import env


class ProviderService(services.ProviderService):
    """Business logic for getting providers."""

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
        cache_path = cast(pathlib.Path, kwargs.get("cache_path", env.get_host_shared_cache_path()))
        our_lock = _maybe_lock_cache(cache_path)

        # Forward the shared cache path.
        kwargs["cache_path"] = cache_path if our_lock else None
        return super().get_base(
            base_name,
            instance_name=instance_name,
            # craft-application annotation is incorrect
            **kwargs,  # type: ignore[arg-type]
        )


def _maybe_lock_cache(path: pathlib.Path) -> bool:
    """Lock the cache so we only have one copy of Charmcraft using it at a time."""
    if fcntl is None:  # Don't lock on Windows - just don't cache.
        return False
    cache_lock_path = path / "charmcraft.lock"

    emit.trace("Attempting to lock the cache path")
    lock_file = cache_lock_path.open("w+")
    try:
        # Exclusive lock, but non-blocking.
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        emit.progress(
            "Shared cache locked by another process; running without cache.", permanent=True
        )
        return False
    else:
        pid = str(os.getpid())
        lock_file.write(pid)
        lock_file.flush()
        os.fsync(lock_file.fileno())
        emit.trace(f"Cache path locked by this process ({pid})")
        atexit.register(fcntl.flock, lock_file, fcntl.LOCK_UN)
        atexit.register(cache_lock_path.unlink, missing_ok=True)

        return True
