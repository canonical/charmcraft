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

"""Charmcraft basic pydantic model."""
from typing import Annotated

import craft_parts.constraints
import pydantic


def _validate_attribute_name(value: str) -> str:
    """Validate attribute name."""
    from charmcraft import linters  # import here to avoid cyclic imports

    valid_names = [
        checker.name
        for checker in linters.CHECKERS
        if checker.check_type == linters.CheckType.ATTRIBUTE
    ]
    if value not in valid_names:
        raise ValueError(f"Bad attribute name {value!r}")
    return value


def _validate_linter_name(value: str) -> str:
    """Validate linter name."""
    from charmcraft import linters  # import here to avoid cyclic imports

    valid_names = [
        checker.name
        for checker in linters.CHECKERS
        if checker.check_type == linters.CheckType.LINT
    ]
    if value not in valid_names:
        raise ValueError(f"Bad lint name {value!r}")
    return value


RelativePath = craft_parts.constraints.RelativePathStr
AttributeName = Annotated[  # TODO: Turn this into a StrEnum
    str,
    pydantic.Field(strict=True),
    pydantic.BeforeValidator(_validate_attribute_name),
]
LinterName = Annotated[
    str,
    pydantic.Field(strict=True),
    pydantic.BeforeValidator(_validate_linter_name),
]
