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

from typing import Any, Dict

import pydantic

from craft_cli import CraftError
from charmcraft.format import format_pydantic_errors
from charmcraft.const import METADATA_FILENAME


class CharmMetadata(pydantic.BaseModel, frozen=True, validate_all=True):
    """Object representing metadata.yaml contents."""

    name: pydantic.StrictStr
    summary: pydantic.StrictStr = ""
    description: pydantic.StrictStr = ""

    @classmethod
    def unmarshal(cls, obj: Dict[str, Any]):
        """Unmarshal object with necessary translations and error handling.

        :returns: valid CharmMetadata.

        :raises CraftError: On failure to unmarshal object.
        """
        try:
            return cls.parse_obj(obj)
        except pydantic.error_wrappers.ValidationError as error:
            raise CraftError(format_pydantic_errors(error.errors(), file_name=METADATA_FILENAME))
