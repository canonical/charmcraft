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
"""Charmcraft metadata pydantic model."""

from typing import TYPE_CHECKING, Any

import pydantic
from craft_application import models
from craft_application.models import base
from craft_cli import CraftError
from typing_extensions import Self, override

from charmcraft import const

if TYPE_CHECKING:
    from charmcraft.models.project import Bundle, Charm
else:
    Charm = Bundle = None


class CharmMetadata(models.BaseMetadata):
    """A charm's metadata.yaml file.

    This model represents the metadata.yaml file that gets placed in the root
    of a charm.
    """

    model_config = pydantic.ConfigDict(
        validate_assignment=True,
        extra="ignore",
        populate_by_name=True,
        alias_generator=base.alias_generator,
    )

    name: models.ProjectName
    display_name: models.ProjectTitle | None = None
    summary: pydantic.StrictStr
    description: pydantic.StrictStr
    maintainers: list[pydantic.StrictStr] | None = None
    assumes: list[str | dict[str, list | dict]] | None = None
    charm_user: str | None = None
    containers: dict[str, Any] | None = None
    devices: dict[str, Any] | None = None
    docs: pydantic.AnyHttpUrl | None = None
    extra_bindings: dict[str, Any] | None = None
    issues: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None
    peers: dict[str, Any] | None = None
    provides: dict[str, Any] | None = None
    requires: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    source: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None
    storage: dict[str, Any] | None = None
    subordinate: bool | None = None
    terms: list[pydantic.StrictStr] | None = None
    website: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None = None

    @classmethod
    def from_charm(cls, charm: Charm) -> Self:
        """Turn a populated charm model into a metadata model.

        Performs the necessary renaming and reorganisation.
        """
        charm_dict = charm.model_dump(
            exclude_none=True,
            by_alias=True,
            exclude_defaults=False,
        )

        # Flatten links and match to the appropriate metadata.yaml schema
        if charm.links is not None:
            links = charm.links.marshal()
            if "documentation" in links:
                charm_dict["docs"] = links.pop("documentation")
            if "contact" in links:
                contact = links.pop("contact")
                if isinstance(contact, str):
                    contact = [contact]
                charm_dict["maintainers"] = contact
            charm_dict.update(links)

        if "title" in charm_dict:
            charm_dict["display-name"] = charm_dict.pop("title")

        return cls.model_validate(charm_dict)


class CharmMetadataLegacy(CharmMetadata):
    """Object representing LEGACY charm metadata.yaml contents.

    This model only supports the legacy charm metadata.yaml format for compatibility.
    New metadata defined in charmcraft.yaml is handled by the CharmcraftProject models.

    specs: https://juju.is/docs/sdk/metadata-yaml
    """

    # These are looser in the metadata.yaml schema than charmcraft requires.
    name: pydantic.StrictStr  # type: ignore[assignment]
    summary: pydantic.StrictStr  # type: ignore[assignment]
    description: pydantic.StrictStr
    display_name: pydantic.StrictStr | None = None  # type: ignore[assignment]

    @override
    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> Self:
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmMetadataLegacy object.

        :raises CraftError: On failure to unmarshal object.
        """
        # convert undocumented "maintainer" to documented "maintainers"
        if "maintainer" in data and "maintainers" in data:
            raise CraftError(
                f"Cannot specify both 'maintainer' and 'maintainers' in {const.METADATA_FILENAME}"
            )

        if "maintainer" in data:
            data["maintainers"] = [data["maintainer"]]
            del data["maintainer"]

        return cls.model_validate(data)


class BundleMetadata(models.BaseMetadata):
    """metadata.yaml for a bundle zip."""

    name: models.ProjectName | None = None
    description: pydantic.StrictStr | None = None

    @classmethod
    def from_bundle(cls, bundle: Bundle) -> Self:
        """Turn a populated bundle model into a metadata.yaml model."""
        bundle_dict = bundle.marshal()
        if "bundle" in bundle_dict:
            return cls.model_validate(bundle_dict["bundle"])
        del bundle_dict["type"]
        return cls.model_validate(bundle_dict)
