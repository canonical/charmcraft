# Copyright 2021-2022 Canonical Ltd.
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

"""Module to work with OCI registries."""

import base64
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
from typing import Any
from urllib.request import parse_http_list, parse_keqv_list

import requests
import requests_unixsocket  # type: ignore[import-untyped]
from craft_cli import CraftError, emit

# some mimetypes
CONFIG_MIMETYPE = "application/vnd.docker.container.image.v1+json"
MANIFEST_V2_MIMETYPE = "application/vnd.docker.distribution.manifest.v2+json"
LAYER_MIMETYPE = "application/vnd.docker.image.rootfs.diff.tar.gzip"
JSON_RELATED_MIMETYPES = {
    "application/json",
    "application/vnd.docker.distribution.manifest.v1+prettyjws",  # signed manifest
    MANIFEST_V2_MIMETYPE,
}
OCTET_STREAM_MIMETYPE = "application/octet-stream"

# downloads and uploads happen in chunks; this size is mostly driven by the usage in the upload
# blob, where the cost in time is similar for small and large chunks (we need to balance having
# it large enough for speed, but not too large because of memory consumption)
CHUNK_SIZE = 2**20


def assert_response_ok(
    response: requests.Response, expected_status: int = 200
) -> dict[str, Any] | None:
    """Assert the response is ok."""
    if response.status_code != expected_status:
        ct = response.headers.get("Content-Type", "")
        if ct.split(";")[0] in JSON_RELATED_MIMETYPES:
            errors = response.json().get("errors")
        else:
            errors = None
        raise CraftError(
            "Wrong status code from server "
            f"(expected={expected_status}, got={response.status_code})",
            details=f"errors={errors} headers={response.headers}",
        )

    if response.headers.get("Content-Type") not in JSON_RELATED_MIMETYPES:
        return None

    result = response.json()
    if "errors" in result:
        raise CraftError("Response with errors from server: {}".format(result["errors"]))
    return result


class OCIRegistry:
    """Interface to a generic OCI Registry."""

    def __init__(self, server, image_name, *, username="", password=""):
        self.server = server
        self.image_name = image_name
        self.auth_token = None

        if username:
            _u_p = f"{username}:{password}"
            self.auth_encoded_credentials = base64.b64encode(_u_p.encode("ascii")).decode("ascii")
        else:
            self.auth_encoded_credentials = None

    def __eq__(self, other):
        return (
            self.server == other.server
            and self.image_name == other.image_name
            and self.auth_encoded_credentials == other.auth_encoded_credentials
        )

    def _authenticate(self, auth_info):
        """Get the auth token."""
        headers = {}
        if self.auth_encoded_credentials is not None:
            headers["Authorization"] = f"Basic {self.auth_encoded_credentials}"

        emit.trace(f"Authenticating! {auth_info}")
        url = "{realm}?service={service}&scope={scope}".format_map(auth_info)
        response = requests.get(url, headers=headers)

        result = assert_response_ok(response)
        return result["token"]

    def _get_url(self, subpath):
        """Build the URL completing the subpath."""
        return f"{self.server}/v2/{self.image_name}/{subpath}"

    def _get_auth_info(self, response):
        """Parse a 401 response and get the needed auth parameters."""
        www_auth = response.headers["Www-Authenticate"]
        if not www_auth.startswith("Bearer "):
            raise ValueError("Bearer not found")
        return parse_keqv_list(parse_http_list(www_auth[7:]))

    def _hit(self, method, url, headers=None, log=True, **kwargs):
        """Hit the specific URL, taking care of the authentication."""
        if headers is None:
            headers = {}
        if self.auth_token is not None:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        if log:
            emit.trace(f"Hitting the registry: {method} {url}")
        response = requests.request(method, url, headers=headers, **kwargs)
        if response.status_code == 401:
            # token expired or missing, let's get another one and retry
            try:
                auth_info = self._get_auth_info(response)
            except (ValueError, KeyError) as exc:
                raise CraftError(f"Bad 401 response: {exc}; headers: {response.headers!r}")
            self.auth_token = self._authenticate(auth_info)
            headers["Authorization"] = f"Bearer {self.auth_token}"
            response = requests.request(method, url, headers=headers, **kwargs)

        return response

    def _is_item_already_uploaded(self, url):
        """Verify if a generic item is uploaded."""
        response = self._hit("HEAD", url)

        if response.status_code == 200:
            # item is there, done!
            uploaded = True
        elif response.status_code == 404:
            # confirmed item is NOT there
            uploaded = False
        else:
            # something else is going on, log what we have and return False so at least
            # we can continue with the upload
            emit.debug(
                f"Bad response when checking for uploaded {url!r}: "
                f"{response.status_code!r} (headers={response.headers})",
            )
            uploaded = False
        return uploaded

    def is_manifest_already_uploaded(self, reference):
        """Verify if the manifest is already uploaded, using a generic reference.

        If yes, return its digest.
        """
        emit.progress("Checking if manifest is already uploaded")
        url = self._get_url(f"manifests/{reference}")
        return self._is_item_already_uploaded(url)

    def is_blob_already_uploaded(self, reference):
        """Verify if the blob is already uploaded, using a generic reference.

        If yes, return its digest.
        """
        emit.progress("Checking if the blob is already uploaded")
        url = self._get_url(f"blobs/{reference}")
        return self._is_item_already_uploaded(url)

    def upload_manifest(self, manifest_data, reference):
        """Upload a manifest."""
        url = self._get_url(f"manifests/{reference}")
        headers = {
            "Content-Type": MANIFEST_V2_MIMETYPE,
        }
        emit.progress(f"Uploading manifest with reference {reference}")
        response = self._hit("PUT", url, headers=headers, data=manifest_data.encode("utf8"))
        assert_response_ok(response, expected_status=201)
        emit.progress("Manifest uploaded OK")

    def upload_blob(self, filepath, size, digest):
        """Upload the blob from a file."""
        # get the first URL to start pushing the blob
        emit.progress("Getting URL to push the blob")
        url = self._get_url("blobs/uploads/")
        response = self._hit("POST", url)
        assert_response_ok(response, expected_status=202)
        upload_url = response.headers["Location"]
        range_from, range_to_inclusive = (int(x) for x in response.headers["Range"].split("-"))
        emit.progress(f"Got upload URL ok with range {range_from}-{range_to_inclusive}")
        if range_from != 0:
            raise CraftError(
                "Server error: bad range received", details=f"Range={response.headers['Range']!r}"
            )

        # this `range_to_inclusive` alteration is a side effect of the range being inclusive. The
        # server tells us that it already has "0-80", means that it has 81 bytes (from 0 to 80
        # inclusive), we set from_position in 81 and read from there. Going down, "0-1" would mean
        # it has bytes 0 and 1; But "0-0" is special, it's what the server returns when it does
        # not have ANY bytes at all. So we comply with Range parameter, but addressing this
        # special case; worst think it could happen is that we start from 0 when the server
        # has 1 byte already, which is not a problem.
        if range_to_inclusive == 0:
            range_to_inclusive = -1
        from_position = range_to_inclusive + 1

        # start the chunked upload
        with open(filepath, "rb") as fh:
            with emit.progress_bar("Uploading...", size) as progress:
                if from_position:
                    fh.seek(from_position)
                    progress.advance(from_position)

                while True:
                    chunk = fh.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    progress.advance(len(chunk))
                    end_position = from_position + len(chunk)
                    headers = {
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"{from_position}-{end_position}",
                        "Content-Type": OCTET_STREAM_MIMETYPE,
                    }
                    response = self._hit(
                        "PATCH", upload_url, headers=headers, data=chunk, log=False
                    )
                    assert_response_ok(response, expected_status=202)

                    upload_url = response.headers["Location"]
                    from_position += len(chunk)
        headers = {
            "Content-Length": "0",
            "Connection": "close",
        }
        emit.progress("Closing the upload")
        closing_url = f"{upload_url}&digest={digest}"

        response = self._hit("PUT", closing_url, headers=headers, data="")
        assert_response_ok(response, expected_status=201)
        emit.progress("Upload finished OK")
        if response.headers["Docker-Content-Digest"] != digest:
            raise CraftError("Server error: the upload is corrupted")


class HashingTemporaryFile(io.FileIO):
    """A temporary file that keeps the hash and length of what is written."""

    def __init__(self):
        tmp_file = tempfile.NamedTemporaryFile(mode="wb", delete=False)
        self.file_handler = tmp_file.file
        super().__init__(tmp_file.name, mode="wb")
        self.total_length = 0
        self.hasher = hashlib.sha256()

    @property
    def hexdigest(self):
        """Calculate the digest."""
        return self.hasher.hexdigest()

    def write(self, data):
        """Intercept real write to feed hasher and length count."""
        self.total_length += len(data)
        self.hasher.update(data)
        super().write(data)


class LocalDockerdInterface:
    """Functionality to interact with a local Docker daemon."""

    # the address of the dockerd socket
    dockerd_socket_baseurl = "http+unix://%2Fvar%2Frun%2Fdocker.sock"

    def __init__(self):
        self.session = requests_unixsocket.Session()

    def get_image_info_from_id(self, image_id: str) -> dict | None:
        """Get the info for a specific image using its id.

        Returns None to flag that the requested id was not found for any reason.
        """
        url = self.dockerd_socket_baseurl + f"/images/{image_id}/json"
        try:
            response = self.session.get(url)
        except requests.exceptions.ConnectionError:
            emit.debug(
                "Cannot connect to /var/run/docker.sock , please ensure dockerd is running.",
            )
            return None

        if response.status_code == 200:
            # image is there, we're fine
            return response.json()

        # 404 is the standard response to "not found", if not exactly that let's log
        # for proper debugging
        if response.status_code != 404:
            emit.debug(f"Bad response when validating local image: {response.status_code}")
            return None
        return None

    def get_image_info_from_digest(self, digest: str) -> dict | None:
        """Get the info for a specific image using its digest.

        Returns None to flag that the requested digest was not found for any reason.
        """
        url = self.dockerd_socket_baseurl + "/images/json"
        try:
            response = self.session.get(url)
        except requests.exceptions.ConnectionError:
            emit.debug(
                "Cannot connect to /var/run/docker.sock , please ensure dockerd is running.",
            )
            return None

        if response.status_code != 200:
            emit.debug(f"Bad response when validating local image: {response.status_code}")
            return None

        for image_info in response.json():
            if image_info["RepoDigests"] is None:
                continue
            if any(digest in repo_digest for repo_digest in image_info["RepoDigests"]):
                return image_info
        return None

    def get_streamed_image_content(self, image_id: str) -> requests.Response:
        """Stream the content of a specific image."""
        url = self.dockerd_socket_baseurl + f"/images/{image_id}/get"
        return self.session.get(url, stream=True)


class ImageHandler:
    """Provide specific functionalities around images."""

    def __init__(self, registry):
        self.registry = registry

    def check_in_registry(self, digest: str) -> bool:
        """Verify if the image is present in the registry."""
        return self.registry.is_manifest_already_uploaded(digest)

    def _extract_file(
        self, image_tar: str, name: str, compress: bool = False
    ) -> tuple[str, int, str]:
        """Extract a file from the tar and return its info. Optionally, gzip the content."""
        emit.progress(f"Extracting file {name!r} from local tar (compress={compress})")
        src_filehandler = image_tar.extractfile(name)
        mtime = image_tar.getmember(name).mtime

        hashing_temp_file = HashingTemporaryFile()
        if compress:
            # open the gzip file using the temporary file handler; use the original name and time
            # as 'filename' and 'mtime' correspondingly as those go to the gzip headers,
            # to ensure same final hash across different runs
            dst_filehandler = gzip.GzipFile(
                fileobj=hashing_temp_file,
                mode="wb",
                filename=os.path.basename(name),
                mtime=mtime,
            )
        else:
            dst_filehandler = hashing_temp_file
        try:
            while True:
                chunk = src_filehandler.read(CHUNK_SIZE)
                if not chunk:
                    break
                dst_filehandler.write(chunk)
        finally:
            dst_filehandler.close()
            # gzip does not automatically close the underlying file handler, let's do it manually
            hashing_temp_file.close()

        digest = f"sha256:{hashing_temp_file.hexdigest}"
        return hashing_temp_file.name, hashing_temp_file.total_length, digest

    def _upload_blob(self, filepath: str, size: int, digest: str) -> None:
        """Upload the blob (if necessary)."""
        # if it's already uploaded, nothing to do
        if self.registry.is_blob_already_uploaded(digest):
            emit.progress("Blob was already uploaded")
        else:
            self.registry.upload_blob(filepath, size, digest)

        # finally remove the temp filepath
        os.unlink(filepath)

    def upload_from_local(self, image_info: dict[str, Any]) -> str | None:
        """Upload the image from the local registry.

        Returns the new remote digest.
        """
        dockerd = LocalDockerdInterface()
        local_image_size = image_info["Size"]
        image_id = image_info["Id"]

        emit.progress(f"Getting the image from the local repo; size={local_image_size}")
        response = dockerd.get_streamed_image_content(image_id)

        tmp_exported = tempfile.NamedTemporaryFile(mode="wb", delete=False)
        with emit.progress_bar("Reading image...", local_image_size) as progress:
            for chunk in response.iter_content(CHUNK_SIZE):
                progress.advance(len(chunk))
                tmp_exported.file.write(chunk)
        tmp_exported.close()

        # open the image tar and inspect it to get the config and layers from the only one
        # manifest inside (as it's a list of one)
        image_tar = tarfile.open(tmp_exported.name)
        local_manifest = json.load(image_tar.extractfile("manifest.json"))
        (local_manifest,) = local_manifest
        config_name = local_manifest.get("Config")
        layer_names = local_manifest["Layers"]
        manifest = {
            "mediaType": MANIFEST_V2_MIMETYPE,
            "schemaVersion": 2,
        }

        if config_name is not None:
            fpath, size, digest = self._extract_file(image_tar, config_name)
            emit.progress(f"Uploading config blob, size={size}, digest={digest}")
            self._upload_blob(fpath, size, digest)
            manifest["config"] = {
                "digest": digest,
                "mediaType": CONFIG_MIMETYPE,
                "size": size,
            }

        manifest["layers"] = manifest_layers = []
        len_layers = len(layer_names)
        for idx, layer_name in enumerate(layer_names, 1):
            fpath, size, digest = self._extract_file(image_tar, layer_name, compress=True)
            emit.progress(f"Uploading layer blob {idx}/{len_layers}, size={size}, digest={digest}")
            self._upload_blob(fpath, size, digest)
            manifest_layers.append(
                {
                    "digest": digest,
                    "mediaType": LAYER_MIMETYPE,
                    "size": size,
                }
            )

        # remove the temp tar file
        os.unlink(tmp_exported.name)

        # upload the manifest
        manifest_data = json.dumps(manifest)
        digest = "sha256:{}".format(hashlib.sha256(manifest_data.encode("utf8")).hexdigest())
        self.registry.upload_manifest(manifest_data, digest)
        return digest
