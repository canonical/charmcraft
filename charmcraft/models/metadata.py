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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import pydantic
from craft_application import models
from craft_cli import CraftError
from typing_extensions import Self

from charmcraft.const import (
    METADATA_FILENAME,
    METADATA_YAML_KEYS,
)

if TYPE_CHECKING:
    from charmcraft.models.project import Bundle, Charm
else:
    Charm = Bundle = None


class CharmMetadata(models.BaseMetadata):
    """A charm's metadata.yaml file.

    This model represents the metadata.yaml file that gets placed in the root
    of a charm.
    """

    name: models.ProjectName
    display_name: Optional[models.ProjectTitle]
    summary: models.SummaryStr
    description: pydantic.StrictStr
    maintainers: Optional[List[pydantic.StrictStr]]
    assumes: Optional[List[Union[str, Dict[str, Union[List, Dict]]]]]
    containers: Optional[Dict[str, Any]]
    devices: Optional[Dict[str, Any]]
    docs: Optional[pydantic.AnyHttpUrl]
    extra_bindings: Optional[Dict[str, Any]]
    issues: Optional[Union[pydantic.AnyHttpUrl, List[pydantic.AnyHttpUrl]]]
    peers: Optional[Dict[str, Any]]
    provides: Optional[Dict[str, Any]]
    requires: Optional[Dict[str, Any]]
    resources: Optional[Dict[str, Any]]
    source: Optional[Union[pydantic.AnyHttpUrl, List[pydantic.AnyHttpUrl]]]
    storage: Optional[Dict[str, Any]]
    subordinate: Optional[bool]
    terms: Optional[List[pydantic.StrictStr]]
    website: Optional[Union[pydantic.AnyHttpUrl, List[pydantic.AnyHttpUrl]]]

    @classmethod
    def from_charm(cls, charm: Charm) -> Self:
        """Turn a populated charm model into a metadata model.

        Performs the necessary renaming and reorganisation.
        """
        charm_dict = charm.dict(
            include=METADATA_YAML_KEYS | {"title"},
            exclude_none=True,
            by_alias=True,
        )

        # Flatten links and match to the appropriate metadata.yaml name
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

        return cls.parse_obj(charm_dict)


class CharmMetadataLegacy(CharmMetadata):
    """Object representing LEGACY charm metadata.yaml contents.

    This model only supports the legacy charm metadata.yaml format for compatibility.
    New metadata defined in charmcraft.yaml is handled by the CharmcraftConfig model.

    specs: https://juju.is/docs/sdk/metadata-yaml
    """

    # These are looser in the metadata.yaml schema than charmcraft requires.
    name: pydantic.StrictStr  # type: ignore[assignment]
    summary: pydantic.StrictStr  # type: ignore[assignment]
    description: pydantic.StrictStr
    display_name: Optional[pydantic.StrictStr]  # type: ignore[assignment]

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmMetadataLegacy object.

        :raises CraftError: On failure to unmarshal object.
        """
        # convert undocumented "maintainer" to documented "maintainers"
        if "maintainer" in obj and "maintainers" in obj:
            raise CraftError(
                f"Cannot specify both 'maintainer' and 'maintainers' in {METADATA_FILENAME}"
            )

        if "maintainer" in obj:
            obj["maintainers"] = [obj["maintainer"]]
            del obj["maintainer"]

        return cls.parse_obj(obj)


class BundleMetadata(models.BaseMetadata):
    """metadata.yaml for a bundle zip."""

    name: models.ProjectName
    description: Optional[pydantic.StrictStr]

    @classmethod
    def from_bundle(cls, bundle: Bundle) -> Self:
        """Turn a populated bundle model into a metadata.yaml model."""
        bundle_dict = bundle.marshal()
        del bundle_dict["type"]
        return cls.parse_obj(bundle_dict)


class BundleMetadataLegacy(BundleMetadata):
    """Object representing LEGACY bundle metadata.yaml contents.

    This model only supports the legacy bundle metadata.yaml format.

    specs: https://juju.is/docs/sdk/metadata-yaml
    """

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid BundleMetadataLegacy.

        :raises CraftError: On failure to unmarshal object.
        """
        return cls.parse_obj(obj)
