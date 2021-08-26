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

"""The Store API handling."""

import logging
import platform
import time
from collections import namedtuple

from craft_store import attenuations
import craft_store
from dateutil import parser
from charmcraft.cmdbase import CommandError

from charmcraft.commands.store.client import Client

logger = logging.getLogger("charmcraft.commands.store")

# helpers to build responses from this layer
User = namedtuple("User", "name username userid")
Entity = namedtuple("Charm", "entity_type name private status")
Uploaded = namedtuple("Uploaded", "ok status revision errors")
# XXX Facundo 2020-07-23: Need to do a massive rename to call `revno` to the "revision as
# the number" inside the "revision as the structure", this gets super confusing in the code with
# time, and now it's the moment to do it (also in Release below!)
Revision = namedtuple("Revision", "revision version created_at status errors bases")
Error = namedtuple("Error", "message code")
Release = namedtuple("Release", "revision channel expires_at resources base")
Channel = namedtuple("Channel", "name fallback track risk branch")
Library = namedtuple("Library", "api content content_hash lib_id lib_name charm_name patch")
Resource = namedtuple("Resource", "name optional revision resource_type")
ResourceRevision = namedtuple("ResourceRevision", "revision created_at size")
RegistryCredentials = namedtuple("RegistryCredentials", "image_name username password")
Base = namedtuple("Base", "architecture channel name")

# those statuses after upload that flag that the review ended (and if it ended succesfully or not)
UPLOAD_ENDING_STATUSES = {
    "approved": True,
    "rejected": False,
}
POLL_DELAY = 1


def _build_errors(item):
    """Build a list of Errors from response item."""
    return [Error(message=e["message"], code=e["code"]) for e in (item["errors"] or [])]


def _build_revision(item):
    """Build a Revision from a response item."""
    bases = [(None if base is None else Base(**base)) for base in item["bases"]]
    rev = Revision(
        revision=item["revision"],
        version=item["version"],
        created_at=parser.parse(item["created-at"]),
        status=item["status"],
        errors=_build_errors(item),
        bases=bases,
    )
    return rev


def _build_resource_revision(item):
    """Build a Revision from a response item."""
    rev = ResourceRevision(
        revision=item["revision"],
        created_at=parser.parse(item["created-at"]),
        size=item["size"],
    )
    return rev


def _build_library(resp):
    """Build a Library from a response."""
    lib = Library(
        api=resp["api"],
        content=resp.get("content"),  # not always present
        content_hash=resp["hash"],
        lib_id=resp["library-id"],
        lib_name=resp["library-name"],
        charm_name=resp["charm-name"],
        patch=resp["patch"],
    )
    return lib


def _build_resource(item):
    """Build a Resource from a response item."""
    resource = Resource(
        name=item["name"],
        optional=item.get("optional"),
        revision=item.get("revision"),
        resource_type=item["type"],
    )
    return resource


def _get_hostname() -> str:
    hostname = platform.node()
    if not hostname:
        hostname = "UNKNOWN"
    return hostname


def _store_client_wrapper(method):
    def error_decorator(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except craft_store.errors.NotLoggedIn as error:
            logger.warning(str(error))
        except craft_store.errors.StoreServerError as error:
            if error.response.status_code == 401:
                # Try to login on 401 error.
                # Evaluate what other errors can be wrapped here.
                logger.warning(
                    f"Store replied [{error.response.status_code}] {error.response.reason}. "
                    "Retrying login."
                )
                self.login()
                return method(self, *args, **kwargs)
            else:
                raise CommandError(str(error)) from error
        except craft_store.errors.CraftStoreError as error:
            raise CommandError(
                f"Server error while communicating to the Store: {error!s}"
            ) from error

    return error_decorator


class Store:
    """The main interface to the Store's API."""

    def __init__(self, charmhub_config):
        self._client = Client(charmhub_config.api_url, charmhub_config.storage_url)

    def login(self):
        """Login into the store.

        The login happens on every request to the Store (if current credentials were not
        enough), so to trigger a new login we...

            - remove local credentials

            - exercise the simplest command regarding developer identity
        """
        hostname = _get_hostname()
        try:
            self._client.login(
                # 3600 * 30
                ttl=108000,
                description=f"charmcraft@{hostname}",
                permissions=[
                    attenuations.ACCOUNT_REGISTER_PACKAGE,
                    attenuations.ACCOUNT_VIEW_PACKAGES,
                    attenuations.PACKAGE_MANAGE,
                    attenuations.PACKAGE_VIEW,
                ],
            )
        except craft_store.errors.CraftStoreError as error:
            raise CommandError(str(error)) from error

    def logout(self):
        """Logout from the store.

        There's no action really in the Store to logout, we just remove local credentials.
        """
        self._client.logout()

    @_store_client_wrapper
    def whoami(self):
        """Return authenticated user details."""
        response = self._client.whoami()

        result = User(
            name=response["display-name"],
            username=response["username"],
            userid=response["id"],
        )
        return result

    @_store_client_wrapper
    def register_name(self, name, entity_type):
        """Register the specified name for the authenticated user."""
        self._client.request_urlpath_json(
            "POST", "/v1/charm", json={"name": name, "type": entity_type}
        )

    @_store_client_wrapper
    def list_registered_names(self):
        """Return names registered by the authenticated user."""
        response = self._client.request_urlpath_json("GET", "/v1/charm")
        result = []
        for item in response["results"]:
            result.append(
                Entity(
                    name=item["name"],
                    private=item["private"],
                    status=item["status"],
                    entity_type=item["type"],
                )
            )
        return result

    def _upload(self, endpoint, filepath, *, extra_fields=None):
        """Upload for all charms, bundles and resources (generic process)."""
        upload_id = self._client.push_file(filepath)
        payload = {"upload-id": upload_id}
        if extra_fields is not None:
            payload.update(extra_fields)
        response = self._client.request_urlpath_json("POST", endpoint, json=payload)
        status_url = response["status-url"]
        logger.debug("Upload %s started, got status url %s", upload_id, status_url)

        while True:
            response = self._client.request_urlpath_json("GET", status_url)
            logger.debug("Status checked: %s", response)

            # as we're asking for a single upload_id, the response will always have only one item
            (revision,) = response["revisions"]
            status = revision["status"]

            if status in UPLOAD_ENDING_STATUSES:
                return Uploaded(
                    ok=UPLOAD_ENDING_STATUSES[status],
                    errors=_build_errors(revision),
                    status=status,
                    revision=revision["revision"],
                )

            # XXX Facundo 2020-06-30: Implement a slight backoff algorithm and fallout after
            # N attempts (which should be big, as per snapcraft experience). Issue: #79.
            time.sleep(POLL_DELAY)

    @_store_client_wrapper
    def upload(self, name, filepath):
        """Upload the content of filepath to the indicated charm."""
        endpoint = f"/v1/charm/{name}/revisions"
        return self._upload(endpoint, filepath)

    @_store_client_wrapper
    def upload_resource(self, charm_name, resource_name, resource_type, filepath):
        """Upload the content of filepath to the indicated resource."""
        endpoint = f"/v1/charm/{charm_name}/resources/{resource_name}/revisions"
        return self._upload(endpoint, filepath, extra_fields={"type": resource_type})

    @_store_client_wrapper
    def list_revisions(self, name):
        """Return charm revisions for the indicated charm."""
        response = self._client.request_urlpath_json("GET", f"/v1/charm/{name}/revisions")
        result = [_build_revision(item) for item in response["revisions"]]
        return result

    @_store_client_wrapper
    def release(self, name, revision, channels, resources):
        """Release one or more revisions for a package."""
        endpoint = "/v1/charm/{}/releases".format(name)
        resources = [{"name": res.name, "revision": res.revision} for res in resources]
        items = [
            {"revision": revision, "channel": channel, "resources": resources}
            for channel in channels
        ]
        self._client.request_urlpath_json("POST", endpoint, json=items)

    @_store_client_wrapper
    def list_releases(self, name):
        """List current releases for a package."""
        endpoint = "/v1/charm/{}/releases".format(name)
        response = self._client.request_urlpath_json("GET", endpoint)

        channel_map = []
        for item in response["channel-map"]:
            expires_at = item["expiration-date"]
            if expires_at is not None:
                # `datetime.datetime.fromisoformat` is available only since Py3.7
                expires_at = parser.parse(expires_at)
            resources = [_build_resource(r) for r in item["resources"]]
            base = None if item["base"] is None else Base(**item["base"])
            channel_map.append(
                Release(
                    revision=item["revision"],
                    channel=item["channel"],
                    expires_at=expires_at,
                    resources=resources,
                    base=base,
                )
            )

        channels = [
            Channel(
                name=item["name"],
                fallback=item["fallback"],
                track=item["track"],
                risk=item["risk"],
                branch=item["branch"],
            )
            for item in response["package"]["channels"]
        ]

        revisions = [_build_revision(item) for item in response["revisions"]]

        return channel_map, channels, revisions

    @_store_client_wrapper
    def create_library_id(self, charm_name, lib_name):
        """Create a new library id."""
        endpoint = f"/v1/charm/libraries/{charm_name}"
        response = self._client.request_urlpath_json("POST", endpoint, {"library-name": lib_name})
        lib_id = response["library-id"]
        return lib_id

    @_store_client_wrapper
    def create_library_revision(self, charm_name, lib_id, api, patch, content, content_hash):
        """Create a new library revision."""
        endpoint = f"/v1/charm/libraries/{charm_name}/{lib_id}"
        payload = {
            "api": api,
            "patch": patch,
            "content": content,
            "hash": content_hash,
        }
        response = self._client.request_urlpath_json("POST", endpoint, json=payload)
        result = _build_library(response)
        return result

    @_store_client_wrapper
    def get_library(self, charm_name, lib_id, api):
        """Get the library tip by id for a given api version."""
        endpoint = f"/v1/charm/libraries/{charm_name}/{lib_id}?api={api}"
        response = self._client.request_urlpath_json("GET", endpoint)
        result = _build_library(response)
        return result

    @_store_client_wrapper
    def get_libraries_tips(self, libraries):
        """Get the tip details for several libraries at once.

        Each requested library can be specified in different ways: using the library id
        or the charm and library names (both will pinpoint the library), but in the later
        case the library name is optional (so all libraries for that charm will be
        returned). Also, for all those cases, an API version can be specified.
        """
        endpoint = "/v1/charm/libraries/bulk"
        payload = []
        for lib in libraries:
            if "lib_id" in lib:
                item = {
                    "library-id": lib["lib_id"],
                }
            else:
                item = {
                    "charm-name": lib["charm_name"],
                }
                if "lib_name" in lib:
                    item["library-name"] = lib["lib_name"]
            if "api" in lib:
                item["api"] = lib["api"]
            payload.append(item)
        response = self._client.request_urlpath_json("POST", endpoint, json=payload)
        libraries = response["libraries"]
        result = {(item["library-id"], item["api"]): _build_library(item) for item in libraries}
        return result

    @_store_client_wrapper
    def list_resources(self, charm):
        """Return resources associated to the indicated charm."""
        response = self._client.request_urlpath_json("GET", f"/v1/charm/{charm}/resources")
        result = [_build_resource(item) for item in response["resources"]]
        return result

    @_store_client_wrapper
    def list_resource_revisions(self, charm_name, resource_name):
        """Return revisions for the indicated charm resource."""
        endpoint = f"/v1/charm/{charm_name}/resources/{resource_name}/revisions"
        response = self._client.request_urlpath_json("GET", endpoint)
        result = [_build_resource_revision(item) for item in response["revisions"]]
        return result

    @_store_client_wrapper
    def get_oci_registry_credentials(self, charm_name, resource_name):
        """Get credentials to upload a resource to the Canonical's OCI Registry."""
        endpoint = f"/v1/charm/{charm_name}/resources/{resource_name}/oci-image/upload-credentials"
        response = self._client.request_urlpath_json("GET", endpoint)
        return RegistryCredentials(
            image_name=response["image-name"],
            username=response["username"],
            password=response["password"],
        )

    @_store_client_wrapper
    def get_oci_image_blob(self, charm_name, resource_name, digest):
        """Get the blob that points to the OCI image in the Canonical's OCI Registry."""
        payload = {"image-digest": digest}
        endpoint = f"/v1/charm/{charm_name}/resources/{resource_name}/oci-image/blob"
        content = self._client.request_urlpath_text("GET", endpoint, json=payload)
        # the response here is returned as is, because it's opaque to charmcraft
        return content
