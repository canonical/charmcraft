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

from typing import Any

import pydantic
from craft_cli import CraftError

from charmcraft import const


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
    assumes: list[str | dict[str, list | dict]] | None
    containers: dict[str, Any] | None
    devices: dict[str, Any] | None
    display_name: pydantic.StrictStr | None
    docs: pydantic.AnyHttpUrl | None
    extra_bindings: dict[str, Any] | None
    issues: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    maintainers: list[pydantic.StrictStr] | None
    peers: dict[str, Any] | None
    provides: dict[str, Any] | None
    requires: dict[str, Any] | None
    resources: dict[str, Any] | None
    source: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None
    storage: dict[str, Any] | None
    subordinate: bool | None
    terms: list[pydantic.StrictStr] | None
    website: pydantic.AnyHttpUrl | list[pydantic.AnyHttpUrl] | None

    @classmethod
    def unmarshal(cls, obj: dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmMetadataLegacy object.

        :raises CraftError: On failure to unmarshal object.
        """
        # convert undocumented "maintainer" to documented "maintainers"
        if "maintainer" in obj and "maintainers" in obj:
            raise CraftError(
                f"Cannot specify both 'maintainer' and 'maintainers' in {const.METADATA_FILENAME}"
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
    description: pydantic.StrictStr | None

    @classmethod
    def unmarshal(cls, obj: dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid BundleMetadataLegacy.

        :raises CraftError: On failure to unmarshal object.
        """
        return cls.parse_obj(obj)
