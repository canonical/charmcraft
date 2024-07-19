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
"""Service class for store interaction."""
from __future__ import annotations

import platform
from collections.abc import Collection, Mapping, Sequence

import craft_application
import craft_store
from craft_cli import emit
from craft_store import models
from overrides import override

from charmcraft import const, env, errors, store
from charmcraft.models import CharmLib
from charmcraft.store import AUTH_DEFAULT_PERMISSIONS, AUTH_DEFAULT_TTL
from charmcraft.store.models import Library, LibraryMetadataRequest


class BaseStoreService(craft_application.AppService):
    """Business logic for interacting with the store.

    This service should be easily adjustable for craft-application.
    """

    ClientClass: type[craft_store.StoreClient] = craft_store.StoreClient
    client: craft_store.StoreClient
    _endpoints: craft_store.endpoints.Endpoints = craft_store.endpoints.CHARMHUB
    _environment_auth: str = const.ALTERNATE_AUTH_ENV_VAR

    @property
    def _user_agent(self) -> str:
        """Get the user agent string for the store service."""
        product = self._app.name
        version = self._app.version
        system_information = self._ua_system_info
        return f"{product.title()}/{version} ({system_information})"

    @property
    def _ua_system_info(self) -> str:
        """System information for user agent."""
        segments = [
            f"{platform.system()} {platform.release()}",
            platform.machine(),
            f"{platform.python_implementation()} {platform.python_version()}",
        ]
        if platform.system() == "Linux":
            import distro

            segments.append(f"{distro.name()} {distro.version()}")

        return "; ".join(segments)

    @property
    def _base_url(self) -> str:
        """Get the store base URL."""
        return env.get_store_config().api_url

    @property
    def _storage_url(self) -> str:
        return env.get_store_config().storage_url

    def setup(self) -> None:
        """Set up the store service."""
        super().setup()

        try:
            self.client = self.ClientClass(
                application_name=self._app.name,
                base_url=self._base_url,
                storage_base_url=self._storage_url,
                endpoints=self._endpoints,
                environment_auth=self._environment_auth,
                user_agent=self._user_agent,
            )
        except craft_store.errors.NoKeyringError:
            emit.progress(
                "WARNING: Cannot get a keyring. Every store interaction that requires "
                "authentication will require you to log in again.",
                permanent=True,
            )
            self.client = self.ClientClass(
                application_name=self._app.name,
                base_url=self._base_url,
                storage_base_url=self._storage_url,
                endpoints=self._endpoints,
                environment_auth=self._environment_auth,
                user_agent=self._user_agent,
                ephemeral=True,
            )

    def _get_description(self, description: str | None = None) -> str:
        """Return the given description or a default one."""
        if description is None:
            return f"{self._app.name}@{platform.node()}"
        return description

    def login(
        self,
        permissions: Sequence[str] = AUTH_DEFAULT_PERMISSIONS,
        description: str | None = None,
        ttl: int = AUTH_DEFAULT_TTL,
        packages: Sequence[craft_store.endpoints.Package] | None = None,
        channels: Sequence[str] | None = None,
    ) -> str:
        """Login to the store."""
        description = self._get_description(description)

        try:
            return self.client.login(
                permissions=permissions,
                description=description,
                ttl=ttl,
                packages=packages,
                channels=channels,
            )
        except craft_store.errors.CredentialsAlreadyAvailable as exc:
            raise errors.CraftError(
                "Cannot login because credentials were found in your system "
                "(which may be no longer valid, though).",
                resolution="Please log out first, then log in again.",
            ) from exc

    def logout(self) -> None:
        """Log out of the store."""
        self.client.logout()

    def get_account_info(self):
        """Get the account details of the logged-in account."""
        return self.client.whoami()["account"]

    def get_credentials(
        self,
        permissions: Sequence[str] = AUTH_DEFAULT_PERMISSIONS,
        description: str | None = None,
        ttl: int = AUTH_DEFAULT_TTL,
        packages: Sequence[craft_store.endpoints.Package] | None = None,
        channels: Sequence[str] | None = None,
    ) -> str:
        """Create a fresh set of login credentials for the store.

        This logs in independent of any credentials currently stored for the application and
        returns the resulting macaroon as a string.
        """
        description = self._get_description(description)

        store = craft_store.StoreClient(
            application_name=self._app.name,
            base_url=self._base_url,
            storage_base_url=self._storage_url,
            endpoints=self._endpoints,
            environment_auth=None,
            user_agent=self._user_agent,
            ephemeral=True,
        )

        return store.login(
            permissions=permissions,
            description=description,
            ttl=ttl,
            packages=packages,
            channels=channels,
        )


class StoreService(BaseStoreService):
    """A Store service specifically for Charmcraft."""

    ClientClass = store.Client
    client: store.Client  # pyright: ignore[reportIncompatibleVariableOverride]
    anonymous_client: store.AnonymousClient

    @override
    def setup(self) -> None:
        """Set up the store service."""
        super().setup()
        self.anonymous_client = store.AnonymousClient(
            api_base_url=self._base_url,
            storage_base_url=self._storage_url,
        )

    def set_resource_revisions_architectures(
        self, name: str, resource_name: str, updates: dict[int, list[str]]
    ) -> Collection[models.resource_revision_model.CharmResourceRevision]:
        """Set the architectures for one or more resource revisions.

        :param name: The name of the charm in the store
        :param resource_name: The name of the specific resource
        :param updates: A mapping of resource revision to its architectures.
        :returns: The updated revisions, as craft_store CharmResourceRevision objects.
        """
        self.client.update_resource_revisions(
            *(
                models.CharmResourceRevisionUpdateRequest(
                    revision=revision,
                    bases=[models.RequestCharmResourceBase(architectures=architectures)],
                )
                for revision, architectures in updates.items()
            ),
            name=name,
            resource_name=resource_name,
        )
        new_revisions = self.client.list_resource_revisions(name=name, resource_name=resource_name)
        return [rev for rev in new_revisions if int(rev.revision) in updates]

    def get_libraries_metadata(self, libraries: Sequence[CharmLib]) -> Sequence[Library]:
        """Get the metadata for one or more charm libraries.

        :param libraries: A sequence of libraries to request.
        :returns: A sequence of the libraries' metadata in the store.
        """
        store_libs = []
        for lib in libraries:
            charm_name, _, lib_name = lib.lib.partition(".")
            store_lib = LibraryMetadataRequest(
                {
                    "charm-name": charm_name,
                    "library-name": lib_name,
                    "api": lib.api_version,
                }
            )
            if (patch_version := lib.patch_version) is not None:
                store_lib["patch"] = patch_version
            store_libs.append(store_lib)

        return self.anonymous_client.fetch_libraries_metadata(store_libs)

    def get_libraries_metadata_by_name(
        self, libraries: Sequence[CharmLib]
    ) -> Mapping[str, Library]:
        """Get a mapping of [charm_name].[library_name] to the requested libraries."""
        return {
            f"{lib.charm_name}.{lib.lib_name}": lib
            for lib in self.get_libraries_metadata(libraries)
        }

    def get_library(
        self, charm_name: str, *, library_id: str, api: int | None = None, patch: int | None = None
    ) -> Library:
        """Get a library by charm name and ID from charmhub."""
        return self.anonymous_client.get_library(
            charm_name=charm_name, library_id=library_id, api=api, patch=patch
        )
