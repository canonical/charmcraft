# Copyright 2020-2021 Canonical Ltd.
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

"""A client to hit the Store."""

import os
import platform
from json.decoder import JSONDecodeError
from typing import Any

import craft_store
import requests
from craft_cli import CraftError, emit
from craft_store import endpoints
from requests_toolbelt import (  # type: ignore[import]
    MultipartEncoder,
    MultipartEncoderMonitor,
)

from charmcraft import __version__, const, utils

TESTING_ENV_PREFIXES = ["TRAVIS", "AUTOPKGTEST_TMP"]


def build_user_agent():
    """Build the charmcraft's user agent."""
    if any(key.startswith(prefix) for prefix in TESTING_ENV_PREFIXES for key in os.environ):
        testing = " (testing) "
    else:
        testing = " "
    os_platform = "{0.system}/{0.release} ({0.machine})".format(utils.get_os_platform())
    return "charmcraft/{}{}{} python/{}".format(
        __version__, testing, os_platform, platform.python_version()
    )


class AnonymousClient:
    """Lightweight layer that access public store data."""

    def __init__(self, api_base_url: str, storage_base_url: str):
        self.api_base_url = api_base_url.rstrip("/")
        self.storage_base_url = storage_base_url.rstrip("/")
        self._http_client = craft_store.http_client.HTTPClient(user_agent=build_user_agent())

    def request_urlpath_text(self, method: str, urlpath: str, *args, **kwargs) -> str:
        """Return a request.Response to a urlpath."""
        return self._http_client.request(method, self.api_base_url + urlpath, *args, **kwargs).text

    def request_urlpath_json(self, method: str, urlpath: str, *args, **kwargs) -> dict[str, Any]:
        """Return .json() from a request.Response to a urlpath."""
        response = self._http_client.request(method, self.api_base_url + urlpath, *args, **kwargs)

        try:
            return response.json()
        except JSONDecodeError as json_error:
            raise CraftError(
                f"Could not retrieve json response ({response.status_code} from request"
            ) from json_error


class Client(craft_store.StoreClient):
    """Lightweight layer above StoreClient."""

    def __init__(self, api_base_url: str, storage_base_url: str, ephemeral: bool = False):
        self.api_base_url = api_base_url.rstrip("/")
        self.storage_base_url = storage_base_url.rstrip("/")

        super().__init__(
            base_url=api_base_url,
            storage_base_url=storage_base_url,
            endpoints=endpoints.CHARMHUB,
            application_name="charmcraft",
            user_agent=build_user_agent(),
            environment_auth=const.ALTERNATE_AUTH_ENV_VAR,
            ephemeral=ephemeral,
        )

    def login(self, *args, **kwargs):
        """Intercept regular login functionality to forbid it when using alternate auth."""
        if os.getenv(const.ALTERNATE_AUTH_ENV_VAR) is not None:
            raise CraftError(
                f"Cannot login when using alternative auth through {const.ALTERNATE_AUTH_ENV_VAR} "
                "environment variable."
            )
        return super().login(*args, **kwargs)

    def logout(self, *args, **kwargs):
        """Intercept regular logout functionality to forbid it when using alternate auth."""
        if os.getenv(const.ALTERNATE_AUTH_ENV_VAR) is not None:
            raise CraftError(
                f"Cannot logout when using alternative auth through {const.ALTERNATE_AUTH_ENV_VAR} "
                "environment variable."
            )
        return super().logout(*args, **kwargs)

    def request_urlpath_text(self, method: str, urlpath: str, *args, **kwargs) -> str:
        """Return a request.Response to a urlpath."""
        return super().request(method, self.api_base_url + urlpath, *args, **kwargs).text

    def request_urlpath_json(self, method: str, urlpath: str, *args, **kwargs) -> dict[str, Any]:
        """Return .json() from a request.Response to a urlpath."""
        response = super().request(method, self.api_base_url + urlpath, *args, **kwargs)

        try:
            return response.json()
        except JSONDecodeError as json_error:
            raise CraftError(
                f"Could not retrieve json response ({response.status_code} from request"
            ) from json_error

    def push_file(self, filepath) -> str:
        """Push the bytes from filepath to the Storage."""
        emit.progress(f"Starting to push {str(filepath)!r}")

        with filepath.open("rb") as fh:
            encoder = MultipartEncoder(
                fields={"binary": (filepath.name, fh, "application/octet-stream")}
            )

            # create a monitor (so that progress can be displayed) as call the real pusher
            monitor = MultipartEncoderMonitor(encoder)
            with emit.progress_bar("Uploading...", monitor.len, delta=False) as progress:
                monitor.callback = lambda mon: progress.advance(mon.bytes_read)
                response = self._storage_push(monitor)

        result = response.json()
        if not result["successful"]:
            raise CraftError(f"Server error while pushing file: {result}")

        upload_id = result["upload_id"]
        emit.progress(f"Uploading bytes ended, id {upload_id}")
        return upload_id

    def _storage_push(self, monitor) -> requests.Response:
        """Push bytes to the storage."""
        return super().request(
            "POST",
            self.storage_base_url + "/unscanned-upload/",
            headers={"Content-Type": monitor.content_type, "Accept": "application/json"},
            data=monitor,
        )
