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

from typing import Any, Dict, Optional, List, Union

import pydantic

from craft_cli import CraftError
from charmcraft.const import METADATA_FILENAME


class CharmMetadataLegacy(
    pydantic.BaseModel,
    extra=pydantic.Extra.allow,
    frozen=True,
    validate_all=True,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Object representing LEGACY charm metadata.yaml contents.

    This model only supports the legacy charm metadata.yaml format for compatibility.
    New metadata defined in charmcraft.yaml is handled by the CharmcraftConfig model.

    specs: https://juju.is/docs/sdk/metadata-yaml
    """

    name: pydantic.StrictStr
    summary: pydantic.StrictStr
    description: pydantic.StrictStr
    assumes: Optional[List[Union[str, Dict[str, Union[List, Dict]]]]]
    containers: Optional[Dict[str, Any]]
    devices: Optional[Dict[str, Any]]
    display_name: Optional[pydantic.StrictStr]
    docs: Optional[pydantic.AnyHttpUrl]
    extra_bindings: Optional[Dict[str, Any]]
    issues: Optional[Union[pydantic.AnyHttpUrl, List[pydantic.AnyHttpUrl]]]
    maintainers: Optional[List[pydantic.StrictStr]]
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


class BundleMetadataLegacy(
    pydantic.BaseModel,
    extra=pydantic.Extra.allow,
    frozen=True,
    validate_all=True,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Object representing LEGACY bundle metadata.yaml contents.

    This model only supports the legacy bundle metadata.yaml format.

    specs: https://juju.is/docs/sdk/metadata-yaml
    """

    name: pydantic.StrictStr
    description: Optional[pydantic.StrictStr]

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid BundleMetadataLegacy.

        :raises CraftError: On failure to unmarshal object.
        """
        return cls.parse_obj(obj)
